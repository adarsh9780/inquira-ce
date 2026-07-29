package manualanalysis

import (
	"context"
	"strings"

	"github.com/adarsh9780/inquira-ce/internal/analysisruntime"
	"github.com/adarsh9780/inquira-ce/internal/apperror"
	"github.com/adarsh9780/inquira-ce/internal/conversation"
	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
)

const maxTimeoutSeconds = 3600

type conversationStore interface {
	CreateConversation(context.Context, conversation.CreateConversationRequest) (conversation.Conversation, error)
	GetConversation(context.Context, string) (conversation.Conversation, error)
	CreateTurn(context.Context, conversation.CreateTurnRequest) (conversation.Turn, error)
	GetTurn(context.Context, string) (conversation.Turn, error)
	MarkFinalTurn(context.Context, string, string) (conversation.Turn, error)
}

type catalogSource interface {
	Prepare(context.Context, string) (datacatalog.Catalog, error)
}

type executor interface {
	Execute(context.Context, analysisruntime.ExecuteRequest, func(analysisruntime.WorkerEvent)) (analysisruntime.ExecuteResult, error)
}

type Service struct {
	conversations conversationStore
	catalog       catalogSource
	executor      executor
}

type RunRequest struct {
	WorkspaceID    string  `json:"workspace_id"`
	ConversationID string  `json:"conversation_id"`
	ParentTurnID   *string `json:"parent_turn_id"`
	Code           string  `json:"code"`
	TimeoutSeconds int     `json:"timeout_seconds"`
}

type RunResult struct {
	Conversation conversation.Conversation     `json:"conversation"`
	Turn         conversation.Turn             `json:"turn"`
	Execution    analysisruntime.ExecuteResult `json:"execution"`
}

func NewService(conversations conversationStore, catalog catalogSource, executor executor) *Service {
	return &Service{conversations: conversations, catalog: catalog, executor: executor}
}

func (s *Service) Run(ctx context.Context, request RunRequest, emit func(analysisruntime.WorkerEvent)) (RunResult, error) {
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	code := strings.TrimSpace(request.Code)
	if workspaceID == "" {
		return RunResult{}, apperror.New("workspace_required", "Choose a workspace before running code.")
	}
	if code == "" {
		return RunResult{}, apperror.New("execution_code_required", "Python code is required for execution.")
	}
	if request.TimeoutSeconds < 1 || request.TimeoutSeconds > maxTimeoutSeconds {
		return RunResult{}, apperror.New("execution_timeout_invalid", "Execution timeout must be between 1 and 3600 seconds.")
	}

	conversationID := strings.TrimSpace(request.ConversationID)
	var ownedConversation conversation.Conversation
	var err error
	if conversationID != "" {
		ownedConversation, err = s.resolveConversation(ctx, workspaceID, conversationID)
		if err != nil {
			return RunResult{}, err
		}
	}
	if _, err := s.catalog.Prepare(ctx, workspaceID); err != nil {
		return RunResult{}, err
	}
	if conversationID == "" {
		ownedConversation, err = s.conversations.CreateConversation(ctx, conversation.CreateConversationRequest{
			WorkspaceID: workspaceID, Title: "Code runs",
		})
		if err != nil {
			return RunResult{}, err
		}
	}
	turn, err := s.conversations.CreateTurn(ctx, conversation.CreateTurnRequest{
		ConversationID: ownedConversation.ID, ParentTurnID: request.ParentTurnID,
		UserText: "Manual code run", MetadataJSON: `{"execution_source":"code_tab"}`,
	})
	if err != nil {
		return RunResult{}, err
	}
	execution, err := s.executor.Execute(ctx, analysisruntime.ExecuteRequest{
		ConversationID: ownedConversation.ID, TurnID: turn.ID, Code: request.Code,
		TimeoutSeconds: request.TimeoutSeconds,
	}, emit)
	if err != nil {
		return RunResult{}, err
	}
	turn, err = s.conversations.GetTurn(ctx, turn.ID)
	if err != nil {
		return RunResult{}, err
	}
	if execution.Success && turn.Status == conversation.TurnStatusCompleted {
		if _, err := s.conversations.MarkFinalTurn(ctx, ownedConversation.ID, turn.ID); err != nil {
			return RunResult{}, err
		}
		ownedConversation, err = s.conversations.GetConversation(ctx, ownedConversation.ID)
		if err != nil {
			return RunResult{}, err
		}
	}
	return RunResult{Conversation: ownedConversation, Turn: turn, Execution: execution}, nil
}

func (s *Service) resolveConversation(ctx context.Context, workspaceID, conversationID string) (conversation.Conversation, error) {
	owned, err := s.conversations.GetConversation(ctx, conversationID)
	if err != nil {
		return conversation.Conversation{}, err
	}
	if owned.WorkspaceID != workspaceID {
		return conversation.Conversation{}, apperror.New("conversation_workspace_mismatch", "Conversation does not belong to this workspace.")
	}
	return owned, nil
}
