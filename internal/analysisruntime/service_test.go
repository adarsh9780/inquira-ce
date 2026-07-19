package analysisruntime

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
	"inquira-go/internal/workspace"
)

type fakeKernelGateway struct {
	request ExecuteWorkerRequest
	result  ExecuteWorkerResult
	err     error
	events  []WorkerEvent
}

func (f *fakeKernelGateway) Execute(_ context.Context, request ExecuteWorkerRequest, emit func(WorkerEvent)) (ExecuteWorkerResult, error) {
	f.request = request
	for _, event := range f.events {
		emit(event)
	}
	if f.err != nil {
		return ExecuteWorkerResult{}, f.err
	}
	for index := range f.result.Artifacts {
		candidate := &f.result.Artifacts[index]
		if candidate.SourcePath == "@staging/data.parquet" {
			candidate.SourcePath = filepath.Join(request.ArtifactDirectory, "data.parquet")
			if err := os.WriteFile(candidate.SourcePath, []byte("PAR1-data"), 0o600); err != nil {
				return ExecuteWorkerResult{}, err
			}
		}
	}
	return f.result, nil
}

func (f *fakeKernelGateway) Status(context.Context, string) (KernelStatus, error) {
	return KernelStatus{Status: "ready"}, nil
}

func (f *fakeKernelGateway) Reset(context.Context, string) (bool, error) { return true, nil }

func (f *fakeKernelGateway) Interrupt(context.Context, string) (bool, error) { return true, nil }

func newExecutionService(t *testing.T, gateway KernelGateway) (*Service, *conversation.Service, conversation.Conversation, conversation.Turn, string) {
	t.Helper()
	root := t.TempDir()
	databasePath := filepath.Join(root, "data", "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	workspaceService := workspace.NewService(workspaceRepository)
	createdWorkspace, err := workspaceService.Create(context.Background(), workspace.CreateRequest{Name: "Analysis"})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = workspaceService.Close() })
	conversationRepository, err := conversation.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	conversationService := conversation.NewService(
		conversationRepository,
		conversation.NewFileHeap(filepath.Join(root, "data", "workspaces")),
	)
	t.Cleanup(func() { _ = conversationService.Close() })
	createdConversation, err := conversationService.CreateConversation(context.Background(), conversation.CreateConversationRequest{
		WorkspaceID: createdWorkspace.ID, Title: "Question",
	})
	if err != nil {
		t.Fatal(err)
	}
	turn, err := conversationService.CreateTurn(context.Background(), conversation.CreateTurnRequest{
		ConversationID: createdConversation.ID, UserText: "What is the total?",
	})
	if err != nil {
		t.Fatal(err)
	}
	catalog := filepath.Join(root, "data", "workspaces", createdWorkspace.ID, "workspace.duckdb")
	if err := os.WriteFile(catalog, []byte("catalog"), 0o600); err != nil {
		t.Fatal(err)
	}
	service := NewService(
		conversationService, gateway,
		filepath.Join(root, "data", "workspaces"), filepath.Join(root, "data", "execution-staging"),
	)
	return service, conversationService, createdConversation, turn, catalog
}

func TestExecutionPublishesWorkerArtifactsAndPersistsTurn(t *testing.T) {
	gateway := &fakeKernelGateway{
		result: ExecuteWorkerResult{
			Success: true, Stdout: "done", ResultKind: "dataframe", ResultName: "totals",
			Variables: map[string]any{"dataframes": map[string]any{}},
			Result:    json.RawMessage(`{"columns":["total"],"rows":[{"total":42}]}`),
			Artifacts: []ArtifactCandidate{{
				Kind: "dataframe", LogicalName: "totals", DisplayName: "Totals",
				PayloadFormat: "parquet", MediaType: "application/vnd.apache.parquet",
				SourcePath: "@staging/data.parquet",
			}},
		},
		events: []WorkerEvent{{Type: "kernel_status", Data: json.RawMessage(`{"status":"busy"}`)}},
	}
	service, conversations, createdConversation, turn, catalog := newExecutionService(t, gateway)
	events := make([]WorkerEvent, 0)
	result, err := service.Execute(context.Background(), ExecuteRequest{
		ConversationID: createdConversation.ID, TurnID: turn.ID,
		Code: "result = conn.sql('select 42 as total').df()", TimeoutSeconds: 30,
	}, func(event WorkerEvent) { events = append(events, event) })
	if err != nil {
		t.Fatal(err)
	}
	if !result.Success || result.ResultKind != "dataframe" || result.ResultName != "totals" || result.Variables == nil || len(result.Artifacts) != 1 {
		t.Fatalf("execution = %#v", result)
	}
	if gateway.request.WorkspaceID != createdConversation.WorkspaceID || gateway.request.DatabasePath != catalog || gateway.request.RunID == "" {
		t.Fatalf("worker request = %#v", gateway.request)
	}
	if len(events) != 1 || events[0].Type != "kernel_status" {
		t.Fatalf("events = %#v", events)
	}
	artifactPath, err := conversations.ArtifactPath(context.Background(), result.Artifacts[0].ID)
	if err != nil {
		t.Fatal(err)
	}
	if contents, err := os.ReadFile(artifactPath); err != nil || string(contents) != "PAR1-data" {
		t.Fatalf("published artifact = %q, %v", contents, err)
	}
	turns, err := conversations.ListTurns(context.Background(), createdConversation.ID)
	if err != nil || len(turns) != 1 {
		t.Fatalf("turns = %#v, %v", turns, err)
	}
	if turns[0].Status != conversation.TurnStatusCompleted || turns[0].CodeSnapshot != gateway.request.Code || turns[0].ResultJSON == "" {
		t.Fatalf("persisted turn = %#v", turns[0])
	}
	if _, err := os.Stat(gateway.request.ArtifactDirectory); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("execution staging was not removed: %v", err)
	}
}

func TestExecutionFailurePersistsTerminalTurnWithoutPublishingArtifacts(t *testing.T) {
	gateway := &fakeKernelGateway{result: ExecuteWorkerResult{
		Success: false, Error: "NameError: missing", Stderr: "traceback", ResultKind: "error",
	}}
	service, conversations, createdConversation, turn, _ := newExecutionService(t, gateway)
	result, err := service.Execute(context.Background(), ExecuteRequest{
		ConversationID: createdConversation.ID, TurnID: turn.ID, Code: "missing", TimeoutSeconds: 30,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.Success || !strings.Contains(result.Error, "NameError") {
		t.Fatalf("execution = %#v", result)
	}
	turns, _ := conversations.ListTurns(context.Background(), createdConversation.ID)
	if turns[0].Status != conversation.TurnStatusFailed || turns[0].CodeSnapshot != "missing" || turns[0].ErrorMessage != result.Error {
		t.Fatalf("failed turn = %#v", turns[0])
	}
}

func TestExecutionRejectsOwnershipTimeoutCatalogAndUnsafeArtifactCandidates(t *testing.T) {
	gateway := &fakeKernelGateway{result: ExecuteWorkerResult{Success: true}}
	service, conversations, createdConversation, turn, catalog := newExecutionService(t, gateway)
	other, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{
		WorkspaceID: createdConversation.WorkspaceID, Title: "Other",
	})
	if err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name    string
		request ExecuteRequest
		code    string
	}{
		{"blank code", ExecuteRequest{ConversationID: createdConversation.ID, TurnID: turn.ID, TimeoutSeconds: 30}, "execution_code_required"},
		{"invalid timeout", ExecuteRequest{ConversationID: createdConversation.ID, TurnID: turn.ID, Code: "1", TimeoutSeconds: 0}, "execution_timeout_invalid"},
		{"wrong owner", ExecuteRequest{ConversationID: other.ID, TurnID: turn.ID, Code: "1", TimeoutSeconds: 30}, "turn_not_found"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if _, err := service.Execute(context.Background(), test.request, nil); appErrorCode(err) != test.code {
				t.Fatalf("error = %v, want %q", err, test.code)
			}
		})
	}
	if err := os.Remove(catalog); err != nil {
		t.Fatal(err)
	}
	if _, err := service.Execute(context.Background(), ExecuteRequest{
		ConversationID: createdConversation.ID, TurnID: turn.ID, Code: "1", TimeoutSeconds: 30,
	}, nil); appErrorCode(err) != "catalog_not_ready" {
		t.Fatalf("missing catalog error = %v", err)
	}
}

func TestExecutionRejectsWorkerArtifactOutsideItsStagingDirectory(t *testing.T) {
	gateway := &fakeKernelGateway{result: ExecuteWorkerResult{
		Success: true,
		Artifacts: []ArtifactCandidate{{
			Kind: "dataframe", LogicalName: "escape", PayloadFormat: "parquet",
			SourcePath: filepath.Join(t.TempDir(), "outside.parquet"),
		}},
	}}
	if err := os.WriteFile(gateway.result.Artifacts[0].SourcePath, []byte("private"), 0o600); err != nil {
		t.Fatal(err)
	}
	service, _, createdConversation, turn, _ := newExecutionService(t, gateway)
	if _, err := service.Execute(context.Background(), ExecuteRequest{
		ConversationID: createdConversation.ID, TurnID: turn.ID, Code: "1", TimeoutSeconds: 30,
	}, nil); appErrorCode(err) != "artifact_candidate_invalid" {
		t.Fatalf("unsafe artifact error = %v", err)
	}
}

func appErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
