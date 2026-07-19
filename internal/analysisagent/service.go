package analysisagent

import (
	"context"
	"encoding/json"
	"strings"
	"unicode/utf8"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
)

const (
	maxTimeoutSeconds = 3600
	maxContextTurns   = 12
	maxQuestionRunes  = 4000
	maxAnswerRunes    = 8000
	maxCodeRunes      = 12000
	maxErrorRunes     = 4000
	maxResultBytes    = 32768
)

type conversationStore interface {
	CreateConversation(context.Context, conversation.CreateConversationRequest) (conversation.Conversation, error)
	GetConversation(context.Context, string) (conversation.Conversation, error)
	ListTurns(context.Context, string) ([]conversation.Turn, error)
	ListArtifacts(context.Context, string) ([]conversation.Artifact, error)
	CreateTurn(context.Context, conversation.CreateTurnRequest) (conversation.Turn, error)
	CompleteTurn(context.Context, conversation.CompleteTurnRequest) (conversation.Turn, error)
	FailTurn(context.Context, conversation.FailTurnRequest) (conversation.Turn, error)
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
		if request.ParentTurnID != nil {
			return AnalyzeResult{}, apperror.New("turn_parent_not_found", "Parent turn not found in this conversation.")
		}
		ownedConversation, err = s.conversations.CreateConversation(ctx, conversation.CreateConversationRequest{
			WorkspaceID: workspaceID, Title: questionTitle(question),
		})
		if err != nil {
			return AnalyzeResult{}, err
		}
	}
	conversationContext, err := s.conversationContext(ctx, ownedConversation.ID, request.ParentTurnID, model.AllowDataSamples)
	if err != nil {
		return AnalyzeResult{}, err
	}
	metadata := contextMetadata(conversationContext, model)
	turn, err := s.conversations.CreateTurn(ctx, conversation.CreateTurnRequest{
		ConversationID: ownedConversation.ID, ParentTurnID: request.ParentTurnID, UserText: question, MetadataJSON: metadata,
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
		RunID: run.ID, ArtifactDirectory: run.StagingDirectory, TimeoutSeconds: request.TimeoutSeconds,
		Model: model, Context: conversationContext, Schema: catalog.AnalysisSchema,
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

func (s *Service) conversationContext(
	ctx context.Context,
	conversationID string,
	parentTurnID *string,
	allowDataSamples bool,
) (ConversationContext, error) {
	result := ConversationContext{Turns: []ContextTurn{}}
	if parentTurnID == nil {
		return result, nil
	}
	parentID := strings.TrimSpace(*parentTurnID)
	if parentID == "" {
		return ConversationContext{}, apperror.New("turn_parent_not_found", "Parent turn not found in this conversation.")
	}
	turns, err := s.conversations.ListTurns(ctx, conversationID)
	if err != nil {
		return ConversationContext{}, err
	}
	byID := make(map[string]conversation.Turn, len(turns))
	for _, turn := range turns {
		byID[turn.ID] = turn
	}
	branch := make([]conversation.Turn, 0, maxContextTurns)
	seen := make(map[string]bool, maxContextTurns)
	currentID := parentID
	for currentID != "" && len(branch) < maxContextTurns {
		if seen[currentID] {
			return ConversationContext{}, apperror.New("turn_context_invalid", "Conversation history contains an invalid parent cycle.")
		}
		seen[currentID] = true
		turn, exists := byID[currentID]
		if !exists {
			return ConversationContext{}, apperror.New("turn_parent_not_found", "Parent turn not found in this conversation.")
		}
		branch = append(branch, turn)
		if turn.ParentTurnID == nil {
			break
		}
		currentID = strings.TrimSpace(*turn.ParentTurnID)
	}
	for left, right := 0, len(branch)-1; left < right; left, right = left+1, right-1 {
		branch[left], branch[right] = branch[right], branch[left]
	}
	for _, turn := range branch {
		artifacts, err := s.conversations.ListArtifacts(ctx, turn.ID)
		if err != nil {
			return ConversationContext{}, err
		}
		contextArtifacts := make([]ContextArtifact, 0, len(artifacts))
		for _, artifact := range artifacts {
			contextArtifacts = append(contextArtifacts, ContextArtifact{
				ArtifactID: artifact.ID, Kind: artifact.Kind, LogicalName: artifact.LogicalName,
				DisplayName: artifact.DisplayName, PayloadFormat: artifact.PayloadFormat,
				MediaType: artifact.MediaType, ByteSize: artifact.ByteSize,
			})
		}
		result.Turns = append(result.Turns, ContextTurn{
			TurnID: turn.ID, Status: turn.Status, UserText: truncateRunes(turn.UserText, maxQuestionRunes),
			AssistantText: truncateRunes(turn.AssistantText, maxAnswerRunes), Code: truncateRunes(turn.CodeSnapshot, maxCodeRunes),
			ResultKind: turn.ResultKind, Result: historicalResult(turn, allowDataSamples),
			Error: truncateRunes(turn.ErrorMessage, maxErrorRunes), Artifacts: contextArtifacts,
		})
	}
	return result, nil
}

func historicalResult(turn conversation.Turn, allowDataSamples bool) json.RawMessage {
	raw := strings.TrimSpace(turn.ResultJSON)
	if raw == "" || raw == "null" {
		return nil
	}
	if allowDataSamples {
		if len(raw) > maxResultBytes {
			return json.RawMessage(`{"omitted":"Historical result exceeded the prompt budget; use its artifact metadata or query the workspace again."}`)
		}
		return json.RawMessage(raw)
	}
	switch strings.ToLower(strings.TrimSpace(turn.ResultKind)) {
	case "dataframe":
		var value map[string]any
		if json.Unmarshal([]byte(raw), &value) != nil {
			return nil
		}
		delete(value, "rows")
		delete(value, "data")
		delete(value, "preview_rows")
		encoded, err := json.Marshal(value)
		if err != nil {
			return nil
		}
		return encoded
	case "figure":
		return nil
	default:
		if len(raw) <= maxResultBytes {
			return json.RawMessage(raw)
		}
		return nil
	}
}

func contextMetadata(history ConversationContext, model modelconfig.RuntimeConfiguration) string {
	turnIDs := make([]string, 0, len(history.Turns))
	for _, turn := range history.Turns {
		turnIDs = append(turnIDs, turn.TurnID)
	}
	encoded, err := json.Marshal(map[string]any{
		"context_turn_ids": turnIDs,
		"model":            map[string]string{"provider": model.Provider, "id": model.Model},
	})
	if err != nil {
		return "{}"
	}
	return string(encoded)
}

func truncateRunes(value string, limit int) string {
	value = strings.TrimSpace(value)
	if utf8.RuneCountInString(value) <= limit {
		return value
	}
	runes := []rune(value)
	return strings.TrimSpace(string(runes[:limit-1])) + "…"
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
