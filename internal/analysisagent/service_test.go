package analysisagent

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
	"inquira-go/internal/workspace"
)

type fakeCatalogSource struct {
	catalog datacatalog.Catalog
	err     error
}

func (f *fakeCatalogSource) Prepare(context.Context, string) (datacatalog.Catalog, error) {
	return f.catalog, f.err
}

type fakeModelSource struct {
	config modelconfig.RuntimeConfiguration
	err    error
}

func (f *fakeModelSource) RuntimeConfiguration(context.Context) (modelconfig.RuntimeConfiguration, error) {
	return f.config, f.err
}

type fakeAgentGateway struct {
	request AgentWorkerRequest
	result  AgentWorkerResult
	err     error
	events  []analysisruntime.WorkerEvent
}

func (f *fakeAgentGateway) Analyze(_ context.Context, request AgentWorkerRequest, emit func(analysisruntime.WorkerEvent)) (AgentWorkerResult, error) {
	f.request = request
	for _, event := range f.events {
		emit(event)
	}
	return f.result, f.err
}

type fakeRuns struct {
	directory  string
	cleaned    bool
	candidates []analysisruntime.ArtifactCandidate
	artifacts  []conversation.Artifact
}

func (f *fakeRuns) PrepareRun() (analysisruntime.Run, error) {
	return analysisruntime.Run{ID: "run-1", StagingDirectory: f.directory}, nil
}

func (f *fakeRuns) CleanupRun(analysisruntime.Run) { f.cleaned = true }

func (f *fakeRuns) PublishCandidates(
	_ context.Context,
	_ conversation.Conversation,
	_ conversation.Turn,
	_ analysisruntime.Run,
	candidates []analysisruntime.ArtifactCandidate,
) ([]conversation.Artifact, error) {
	f.candidates = candidates
	return f.artifacts, nil
}

func newAgentService(t *testing.T, gateway *fakeAgentGateway) (*Service, *conversation.Service, string, *fakeRuns) {
	t.Helper()
	root := t.TempDir()
	database := filepath.Join(root, "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	workspaces := workspace.NewService(workspaceRepository)
	createdWorkspace, err := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "Analysis"})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = workspaces.Close() })
	conversationRepository, err := conversation.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	conversations := conversation.NewService(conversationRepository, conversation.NewFileHeap(filepath.Join(root, "workspaces")))
	t.Cleanup(func() { _ = conversations.Close() })
	catalogPath := filepath.Join(root, "workspace.duckdb")
	if err := os.WriteFile(catalogPath, []byte("catalog"), 0o600); err != nil {
		t.Fatal(err)
	}
	runs := &fakeRuns{directory: filepath.Join(root, "staging"), artifacts: []conversation.Artifact{{ID: "artifact-1"}}}
	service := NewService(
		conversations,
		&fakeCatalogSource{catalog: datacatalog.Catalog{WorkspaceID: createdWorkspace.ID, DatabasePath: catalogPath}},
		&fakeModelSource{config: modelconfig.RuntimeConfiguration{Provider: "openai", Model: "gpt-test", APIKey: "runtime-secret"}},
		gateway,
		runs,
	)
	return service, conversations, createdWorkspace.ID, runs
}

func TestAnalyzeCreatesConversationExecutesAndPersistsTurn(t *testing.T) {
	executionResult := json.RawMessage(`{"columns":["total"],"rows":[{"total":42}]}`)
	gateway := &fakeAgentGateway{
		result: AgentWorkerResult{
			Success: true, Answer: "Total sales are 42.", Code: "result = conn.sql('select 42').df()",
			Execution: analysisruntime.ExecuteWorkerResult{
				Success: true, Result: executionResult, ResultKind: "dataframe",
				Artifacts: []analysisruntime.ArtifactCandidate{{Kind: "dataframe", SourcePath: "/staging/data.parquet"}},
			},
		},
		events: []analysisruntime.WorkerEvent{{Type: "agent_status", Data: map[string]any{"stage": "executing"}}},
	}
	service, conversations, workspaceID, runs := newAgentService(t, gateway)
	result, err := service.Analyze(context.Background(), AnalyzeRequest{
		WorkspaceID: workspaceID, Question: "What are total sales?", TimeoutSeconds: 30,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.Conversation.ID == "" || result.Turn.ID == "" || result.Answer != gateway.result.Answer || !result.Execution.Success {
		t.Fatalf("result = %#v", result)
	}
	if gateway.request.Model.APIKey != "runtime-secret" || gateway.request.DatabasePath == "" || gateway.request.RunID != "run-1" {
		t.Fatalf("worker request = %#v", gateway.request)
	}
	if !runs.cleaned || len(runs.candidates) != 1 || len(result.Artifacts) != 1 {
		t.Fatalf("run state: cleaned=%v candidates=%#v result=%#v", runs.cleaned, runs.candidates, result.Artifacts)
	}
	turn, err := conversations.GetTurn(context.Background(), result.Turn.ID)
	if err != nil {
		t.Fatal(err)
	}
	encoded, _ := json.Marshal(turn)
	if turn.Status != conversation.TurnStatusCompleted || turn.AssistantText != gateway.result.Answer || turn.CodeSnapshot != gateway.result.Code ||
		turn.ResultJSON != string(executionResult) || strings.Contains(string(encoded), "runtime-secret") {
		t.Fatalf("persisted turn = %s", encoded)
	}
}

func TestAnalyzeUsesOwnedConversationAndFailsTerminalTurnWhenWorkerFails(t *testing.T) {
	gateway := &fakeAgentGateway{err: errors.New("provider offline")}
	service, conversations, workspaceID, _ := newAgentService(t, gateway)
	created, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: workspaceID, Title: "Existing"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = service.Analyze(context.Background(), AnalyzeRequest{
		WorkspaceID: workspaceID, ConversationID: created.ID, Question: "Question", TimeoutSeconds: 30,
	}, nil)
	if appErrorCode(err) != "agent_failed" {
		t.Fatalf("error = %v", err)
	}
	turns, listErr := conversations.ListTurns(context.Background(), created.ID)
	if listErr != nil || len(turns) != 1 || turns[0].Status != conversation.TurnStatusFailed {
		t.Fatalf("turns = %#v, %v", turns, listErr)
	}
	if !strings.Contains(turns[0].ErrorMessage, "could not complete") || strings.Contains(turns[0].ErrorMessage, "provider offline") {
		t.Fatalf("unsafe failure message = %q", turns[0].ErrorMessage)
	}
}

func TestAnalyzeRejectsConversationFromAnotherWorkspaceAndInvalidInput(t *testing.T) {
	gateway := &fakeAgentGateway{}
	service, conversations, workspaceID, _ := newAgentService(t, gateway)
	created, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: workspaceID, Title: "Existing"})
	if err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name    string
		request AnalyzeRequest
		code    string
	}{
		{"workspace required", AnalyzeRequest{Question: "Q", TimeoutSeconds: 30}, "workspace_required"},
		{"question required", AnalyzeRequest{WorkspaceID: workspaceID, TimeoutSeconds: 30}, "question_required"},
		{"timeout invalid", AnalyzeRequest{WorkspaceID: workspaceID, Question: "Q"}, "agent_timeout_invalid"},
		{"wrong workspace", AnalyzeRequest{WorkspaceID: "other", ConversationID: created.ID, Question: "Q", TimeoutSeconds: 30}, "conversation_workspace_mismatch"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if _, err := service.Analyze(context.Background(), test.request, nil); appErrorCode(err) != test.code {
				t.Fatalf("error = %v, want %s", err, test.code)
			}
		})
	}
}

func appErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
