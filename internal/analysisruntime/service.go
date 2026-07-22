package analysisruntime

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"

	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
)

const maxTimeoutSeconds = 3600

type conversationStore interface {
	GetConversation(context.Context, string) (conversation.Conversation, error)
	GetTurn(context.Context, string) (conversation.Turn, error)
	CompleteTurn(context.Context, conversation.CompleteTurnRequest) (conversation.Turn, error)
	FailTurn(context.Context, conversation.FailTurnRequest) (conversation.Turn, error)
	PublishArtifact(context.Context, conversation.PublishArtifactRequest, io.Reader) (conversation.Artifact, error)
}

type KernelGateway interface {
	Execute(context.Context, ExecuteWorkerRequest, func(WorkerEvent)) (ExecuteWorkerResult, error)
	Status(context.Context, string) (KernelStatus, error)
	Reset(context.Context, string) (bool, error)
	Interrupt(context.Context, string) (bool, error)
}

type Service struct {
	conversations conversationStore
	kernels       KernelGateway
	workspaceRoot string
	stagingRoot   string
}

func NewService(conversations conversationStore, kernels KernelGateway, workspaceRoot, stagingRoot string) *Service {
	return &Service{
		conversations: conversations, kernels: kernels,
		workspaceRoot: filepath.Clean(workspaceRoot), stagingRoot: filepath.Clean(stagingRoot),
	}
}

func (s *Service) Execute(ctx context.Context, request ExecuteRequest, emit func(WorkerEvent)) (ExecuteResult, error) {
	conversationID := strings.TrimSpace(request.ConversationID)
	turnID := strings.TrimSpace(request.TurnID)
	code := strings.TrimSpace(request.Code)
	if conversationID == "" {
		return ExecuteResult{}, apperror.New("conversation_required", "Conversation identity is required for execution.")
	}
	if turnID == "" {
		return ExecuteResult{}, apperror.New("turn_required", "Turn identity is required for execution.")
	}
	if code == "" {
		return ExecuteResult{}, apperror.New("execution_code_required", "Python code is required for execution.")
	}
	if request.TimeoutSeconds < 1 || request.TimeoutSeconds > maxTimeoutSeconds {
		return ExecuteResult{}, apperror.New("execution_timeout_invalid", "Execution timeout must be between 1 and 3600 seconds.")
	}
	ownedConversation, err := s.conversations.GetConversation(ctx, conversationID)
	if err != nil {
		return ExecuteResult{}, err
	}
	turn, err := s.conversations.GetTurn(ctx, turnID)
	if err != nil || turn.ConversationID != conversationID {
		return ExecuteResult{}, apperror.New("turn_not_found", "Turn not found in this conversation.")
	}
	if turn.Status != conversation.TurnStatusQueued && turn.Status != conversation.TurnStatusRunning {
		return ExecuteResult{}, apperror.New("turn_state_invalid", "Turn is already in a terminal state.")
	}
	catalog, err := s.catalogPath(ownedConversation.WorkspaceID)
	if err != nil {
		return ExecuteResult{}, apperror.New("catalog_not_ready", "Prepare the workspace analysis catalog before running Python.")
	}
	run, err := s.PrepareRun()
	if err != nil {
		return ExecuteResult{}, apperror.Wrap("execution_staging_failed", "Could not prepare execution staging.", err)
	}
	defer s.CleanupRun(run)
	workerResult, err := s.kernels.Execute(ctx, ExecuteWorkerRequest{
		WorkspaceID: ownedConversation.WorkspaceID, DatabasePath: catalog, Code: request.Code,
		RunID: run.ID, ArtifactDirectory: run.StagingDirectory, TimeoutSeconds: request.TimeoutSeconds,
	}, emitOrDiscard(emit))
	if err != nil {
		persistContext := ctx
		if ctx.Err() != nil {
			persistContext = context.WithoutCancel(ctx)
			_, _ = s.kernels.Interrupt(context.Background(), ownedConversation.WorkspaceID)
		}
		message := "The Python runtime could not execute this turn."
		_, _ = s.conversations.FailTurn(persistContext, conversation.FailTurnRequest{
			TurnID: turnID, AssistantText: request.AssistantText, CodeSnapshot: request.Code, ErrorMessage: message,
			MetadataJSON:   request.MetadataJSON,
			ToolEventsJSON: executionEventsJSON(false, "", "", message, false),
		})
		return ExecuteResult{}, apperror.Wrap("execution_failed", message, err)
	}
	result := ExecuteResult{
		RunID: run.ID, Success: workerResult.Success, Stdout: workerResult.Stdout, Stderr: workerResult.Stderr,
		Error: workerResult.Error, Result: workerResult.Result, ResultKind: workerResult.ResultKind,
		ResultName: workerResult.ResultName, Variables: workerResult.Variables,
		Artifacts: make([]conversation.Artifact, 0, len(workerResult.Artifacts)), TimedOut: workerResult.TimedOut,
	}
	if !workerResult.Success {
		message := strings.TrimSpace(workerResult.Error)
		if message == "" {
			message = "Python execution failed."
		}
		if _, err := s.conversations.FailTurn(ctx, conversation.FailTurnRequest{
			TurnID: turnID, AssistantText: request.AssistantText, CodeSnapshot: request.Code, ErrorMessage: message,
			MetadataJSON:   request.MetadataJSON,
			ToolEventsJSON: executionEventsJSON(false, workerResult.Stdout, workerResult.Stderr, message, workerResult.TimedOut),
		}); err != nil {
			return ExecuteResult{}, err
		}
		result.Error = message
		return result, nil
	}
	result.Artifacts, err = s.PublishCandidates(ctx, ownedConversation, turn, run, workerResult.Artifacts)
	if err != nil {
		_, _ = s.conversations.FailTurn(ctx, conversation.FailTurnRequest{
			TurnID: turnID, AssistantText: request.AssistantText, CodeSnapshot: request.Code, ErrorMessage: err.Error(),
			MetadataJSON:   request.MetadataJSON,
			ToolEventsJSON: executionEventsJSON(false, workerResult.Stdout, workerResult.Stderr, err.Error(), false),
		})
		return ExecuteResult{}, err
	}
	resultJSON := ""
	if len(workerResult.Result) > 0 && string(workerResult.Result) != "null" {
		resultJSON = string(workerResult.Result)
	}
	assistantText := request.AssistantText
	if request.UseResultOutput {
		var envelope struct {
			Output string `json:"output"`
		}
		if json.Unmarshal(workerResult.Result, &envelope) == nil && strings.TrimSpace(envelope.Output) != "" {
			assistantText = strings.TrimSpace(envelope.Output)
		}
	}
	if _, err := s.conversations.CompleteTurn(ctx, conversation.CompleteTurnRequest{
		TurnID: turnID, AssistantText: assistantText, CodeSnapshot: request.Code, ResultJSON: resultJSON,
		MetadataJSON:   request.MetadataJSON,
		ResultKind:     workerResult.ResultKind,
		ToolEventsJSON: executionEventsJSON(true, workerResult.Stdout, workerResult.Stderr, "", false),
	}); err != nil {
		return ExecuteResult{}, err
	}
	return result, nil
}

func (s *Service) catalogPath(workspaceID string) (string, error) {
	root, err := filepath.Abs(s.workspaceRoot)
	if err != nil {
		return "", err
	}
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	expected := filepath.Join(root, workspaceID, "workspace.duckdb")
	resolved, err := filepath.EvalSymlinks(expected)
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(resolvedRoot, resolved)
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) {
		return "", errors.New("catalog escaped workspace storage")
	}
	if filepath.Clean(relative) != filepath.Join(workspaceID, "workspace.duckdb") {
		return "", errors.New("catalog path did not match workspace ownership")
	}
	info, err := os.Stat(resolved)
	if err != nil || !info.Mode().IsRegular() {
		return "", errors.New("catalog is not a regular file")
	}
	return expected, nil
}

func (s *Service) prepareStaging(runID string) (string, error) {
	if err := os.MkdirAll(s.stagingRoot, 0o700); err != nil {
		return "", err
	}
	info, err := os.Lstat(s.stagingRoot)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return "", errors.New("execution staging root is not a real directory")
	}
	staging := filepath.Join(s.stagingRoot, runID)
	if err := os.Mkdir(staging, 0o700); err != nil {
		return "", err
	}
	return staging, nil
}

func (s *Service) PrepareRun() (Run, error) {
	runID := uuid.NewString()
	staging, err := s.prepareStaging(runID)
	if err != nil {
		return Run{}, err
	}
	return Run{ID: runID, StagingDirectory: staging}, nil
}

func (s *Service) CleanupRun(run Run) {
	if strings.TrimSpace(run.StagingDirectory) != "" {
		_ = os.RemoveAll(run.StagingDirectory)
	}
}

func (s *Service) PublishCandidates(
	ctx context.Context,
	ownedConversation conversation.Conversation,
	turn conversation.Turn,
	run Run,
	candidates []ArtifactCandidate,
) ([]conversation.Artifact, error) {
	artifacts := make([]conversation.Artifact, 0, len(candidates))
	for _, candidate := range candidates {
		artifact, err := s.publishCandidate(ctx, ownedConversation, turn, run.StagingDirectory, candidate)
		if err != nil {
			return nil, err
		}
		artifacts = append(artifacts, artifact)
	}
	return artifacts, nil
}

func (s *Service) Status(ctx context.Context, workspaceID string) (KernelStatus, error) {
	id := strings.TrimSpace(workspaceID)
	if id == "" {
		return KernelStatus{}, apperror.New("workspace_required", "Workspace identity is required.")
	}
	status, err := s.kernels.Status(ctx, id)
	if err != nil {
		return KernelStatus{}, apperror.Wrap("kernel_status_failed", "Could not load Python kernel status.", err)
	}
	return status, nil
}

func (s *Service) Reset(ctx context.Context, workspaceID string) (bool, error) {
	reset, err := s.kernels.Reset(ctx, strings.TrimSpace(workspaceID))
	if err != nil {
		return false, apperror.Wrap("kernel_reset_failed", "Could not reset the Python kernel.", err)
	}
	return reset, nil
}

func (s *Service) Interrupt(ctx context.Context, workspaceID string) (bool, error) {
	interrupted, err := s.kernels.Interrupt(ctx, strings.TrimSpace(workspaceID))
	if err != nil {
		return false, apperror.Wrap("kernel_interrupt_failed", "Could not interrupt the Python kernel.", err)
	}
	return interrupted, nil
}

func (s *Service) publishCandidate(
	ctx context.Context,
	ownedConversation conversation.Conversation,
	turn conversation.Turn,
	staging string,
	candidate ArtifactCandidate,
) (conversation.Artifact, error) {
	source := filepath.Clean(strings.TrimSpace(candidate.SourcePath))
	resolvedStaging, err := filepath.EvalSymlinks(staging)
	if err != nil {
		return conversation.Artifact{}, apperror.Wrap("artifact_candidate_invalid", "Execution artifact staging is invalid.", err)
	}
	resolvedSource, err := filepath.EvalSymlinks(source)
	if err != nil {
		return conversation.Artifact{}, apperror.Wrap("artifact_candidate_invalid", "Execution artifact is missing or invalid.", err)
	}
	relative, err := filepath.Rel(resolvedStaging, resolvedSource)
	if err != nil || relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) {
		return conversation.Artifact{}, apperror.New("artifact_candidate_invalid", "Execution artifact escaped its staging directory.")
	}
	info, err := os.Stat(resolvedSource)
	if err != nil || !info.Mode().IsRegular() {
		return conversation.Artifact{}, apperror.New("artifact_candidate_invalid", "Execution artifact is not a regular file.")
	}
	file, err := os.Open(resolvedSource)
	if err != nil {
		return conversation.Artifact{}, apperror.Wrap("artifact_candidate_invalid", "Could not open the execution artifact.", err)
	}
	defer file.Close()
	artifact, err := s.conversations.PublishArtifact(ctx, conversation.PublishArtifactRequest{
		ConversationID: ownedConversation.ID, TurnID: turn.ID, Kind: candidate.Kind,
		LogicalName: candidate.LogicalName, DisplayName: candidate.DisplayName,
		PayloadFormat: candidate.PayloadFormat, MediaType: candidate.MediaType,
	}, file)
	if err != nil {
		return conversation.Artifact{}, err
	}
	return artifact, nil
}

func emitOrDiscard(emit func(WorkerEvent)) func(WorkerEvent) {
	if emit != nil {
		return emit
	}
	return func(WorkerEvent) {}
}

func executionEventsJSON(success bool, stdout, stderr, errorMessage string, timedOut bool) string {
	encoded, err := json.Marshal([]map[string]any{{
		"type": "python_execution", "success": success, "stdout": stdout, "stderr": stderr,
		"error": errorMessage, "timed_out": timedOut,
	}})
	if err != nil {
		return "[]"
	}
	return string(encoded)
}
