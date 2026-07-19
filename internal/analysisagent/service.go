package analysisagent

import (
	"context"
	"encoding/json"
	"io"
	"strings"
	"unicode/utf8"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
)

const maxTimeoutSeconds = 3600

type conversationStore interface {
	CreateConversation(context.Context, conversation.CreateConversationRequest) (conversation.Conversation, error)
	GetConversation(context.Context, string) (conversation.Conversation, error)
	CreateTurn(context.Context, conversation.CreateTurnRequest) (conversation.Turn, error)
	CompleteTurn(context.Context, conversation.CompleteTurnRequest) (conversation.Turn, error)
	FailTurn(context.Context, conversation.FailTurnRequest) (conversation.Turn, error)
	PublishArtifact(context.Context, conversation.PublishArtifactRequest, io.Reader) (conversation.Artifact, error)
}

type catalogSource interface {
	Prepare(context.Context, string) (datacatalog.Catalog, error)
}

type modelSource interface {
	RuntimeConfiguration(context.Context) (modelconfig.RuntimeConfiguration, error)
}

type agentGateway interface {
	Analyze(context.Context, AgentWorkerRequest, func(analysisruntime.WorkerEvent)) (AgentWorkerResult, error)
}

type runStore interface {
	PrepareRun() (analysisruntime.Run, error)
	CleanupRun(analysisruntime.Run)
	PublishCandidates(context.Context, conversation.Conversation, conversation.Turn, analysisruntime.Run, []analysisruntime.ArtifactCandidate) ([]conversation.Artifact, error)
}

type Service struct {
	conversations conversationStore
	catalogs      catalogSource
	models        modelSource
	agent         agentGateway
	runs          runStore
}

func NewService(conversations conversationStore, catalogs catalogSource, models modelSource, agent agentGateway, runs runStore) *Service {
	return &Service{conversations: conversations, catalogs: catalogs, models: models, agent: agent, runs: runs}
}

func (s *Service) Analyze(ctx context.Context, request AnalyzeRequest, emit func(analysisruntime.WorkerEvent)) (AnalyzeResult, error) {
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	question := strings.TrimSpace(request.Question)
	if workspaceID == "" {
		return AnalyzeResult{}, apperror.New("workspace_required", "Choose a workspace before asking a question.")
	}
	if question == "" {
		return AnalyzeResult{}, apperror.New("question_required", "Enter a question before starting an analysis.")
	}
	if request.TimeoutSeconds < 1 || request.TimeoutSeconds > maxTimeoutSeconds {
		return AnalyzeResult{}, apperror.New("agent_timeout_invalid", "Analysis timeout must be between 1 and 3600 seconds.")
	}

	var ownedConversation conversation.Conversation
	conversationID := strings.TrimSpace(request.ConversationID)
	if conversationID != "" {
		var err error
		ownedConversation, err = s.conversations.GetConversation(ctx, conversationID)
		if err != nil {
			return AnalyzeResult{}, err
		}
		if ownedConversation.WorkspaceID != workspaceID {
			return AnalyzeResult{}, apperror.New("conversation_workspace_mismatch", "Conversation does not belong to this workspace.")
		}
	}

	catalog, err := s.catalogs.Prepare(ctx, workspaceID)
	if err != nil {
		return AnalyzeResult{}, err
	}
	if catalog.WorkspaceID != workspaceID || strings.TrimSpace(catalog.DatabasePath) == "" {
		return AnalyzeResult{}, apperror.New("catalog_invalid_result", "The workspace analysis catalog is invalid.")
	}
	model, err := s.models.RuntimeConfiguration(ctx)
	if err != nil {
		return AnalyzeResult{}, err
	}
	if conversationID == "" {
		ownedConversation, err = s.conversations.CreateConversation(ctx, conversation.CreateConversationRequest{
			WorkspaceID: workspaceID, Title: questionTitle(question),
		})
		if err != nil {
			return AnalyzeResult{}, err
		}
	}
	turn, err := s.conversations.CreateTurn(ctx, conversation.CreateTurnRequest{
		ConversationID: ownedConversation.ID, ParentTurnID: request.ParentTurnID, UserText: question,
	})
	if err != nil {
		return AnalyzeResult{}, err
	}
	run, err := s.runs.PrepareRun()
	if err != nil {
		return AnalyzeResult{}, s.fail(ctx, turn.ID, "", "Could not prepare analysis storage.", err)
	}
	defer s.runs.CleanupRun(run)
	events := make([]analysisruntime.WorkerEvent, 0)
	forward := func(event analysisruntime.WorkerEvent) {
		events = append(events, event)
		if emit != nil {
			emit(event)
		}
	}
	workerResult, err := s.agent.Analyze(ctx, AgentWorkerRequest{
		WorkspaceID: workspaceID, DatabasePath: catalog.DatabasePath, Question: question,
		RunID: run.ID, ArtifactDirectory: run.StagingDirectory, TimeoutSeconds: request.TimeoutSeconds, Model: model,
	}, forward)
	if err != nil {
		persistContext := ctx
		if ctx.Err() != nil {
			persistContext = context.WithoutCancel(ctx)
		}
		message := "The analysis agent could not complete this turn."
		_, _ = s.conversations.FailTurn(persistContext, conversation.FailTurnRequest{
			TurnID: turn.ID, ErrorMessage: message, ToolEventsJSON: eventsJSON(events),
		})
		return AnalyzeResult{}, apperror.Wrap("agent_failed", message, err)
	}
	if !workerResult.Success {
		message := strings.TrimSpace(workerResult.Error)
		if message == "" {
			message = "The analysis agent could not produce a working answer."
		}
		_, persistErr := s.conversations.FailTurn(ctx, conversation.FailTurnRequest{
			TurnID: turn.ID, AssistantText: workerResult.Answer, CodeSnapshot: workerResult.Code,
			ErrorMessage: message, ToolEventsJSON: eventsJSON(events),
		})
		if persistErr != nil {
			return AnalyzeResult{}, persistErr
		}
		return AnalyzeResult{Conversation: ownedConversation, Turn: turn, Answer: workerResult.Answer, Code: workerResult.Code, RunID: run.ID, Execution: workerResult.Execution}, nil
	}
	artifacts, err := s.runs.PublishCandidates(ctx, ownedConversation, turn, run, workerResult.Execution.Artifacts)
	if err != nil {
		return AnalyzeResult{}, s.fail(ctx, turn.ID, workerResult.Code, "Could not save an analysis artifact.", err)
	}
	resultJSON := ""
	if len(workerResult.Execution.Result) > 0 && string(workerResult.Execution.Result) != "null" {
		resultJSON = string(workerResult.Execution.Result)
	}
	completed, err := s.conversations.CompleteTurn(ctx, conversation.CompleteTurnRequest{
		TurnID: turn.ID, AssistantText: workerResult.Answer, CodeSnapshot: workerResult.Code,
		ToolEventsJSON: eventsJSON(events), ResultJSON: resultJSON, ResultKind: workerResult.Execution.ResultKind,
	})
	if err != nil {
		return AnalyzeResult{}, err
	}
	return AnalyzeResult{
		Conversation: ownedConversation, Turn: completed, Answer: workerResult.Answer, Code: workerResult.Code,
		RunID: run.ID, Execution: workerResult.Execution, Artifacts: artifacts,
	}, nil
}

func (s *Service) fail(ctx context.Context, turnID, code, message string, cause error) error {
	_, _ = s.conversations.FailTurn(ctx, conversation.FailTurnRequest{
		TurnID: turnID, CodeSnapshot: code, ErrorMessage: message, ToolEventsJSON: "[]",
	})
	return apperror.Wrap("agent_failed", message, cause)
}

func questionTitle(question string) string {
	const limit = 80
	if utf8.RuneCountInString(question) <= limit {
		return question
	}
	runes := []rune(question)
	return strings.TrimSpace(string(runes[:limit-1])) + "…"
}

func eventsJSON(events []analysisruntime.WorkerEvent) string {
	encoded, err := json.Marshal(events)
	if err != nil {
		return "[]"
	}
	return string(encoded)
}
