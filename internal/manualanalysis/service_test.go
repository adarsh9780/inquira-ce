package manualanalysis

import (
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"testing"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/workspace"
)

type fakeCatalog struct {
	calls int
	err   error
}

func (f *fakeCatalog) Prepare(_ context.Context, workspaceID string) (datacatalog.Catalog, error) {
	f.calls++
	if f.err != nil {
		return datacatalog.Catalog{}, f.err
	}
	return datacatalog.Catalog{WorkspaceID: workspaceID, DatabasePath: "/catalog.duckdb"}, nil
}

type fakeExecutor struct {
	request       analysisruntime.ExecuteRequest
	conversations *conversation.Service
	fail          bool
}

func (f *fakeExecutor) Execute(ctx context.Context, request analysisruntime.ExecuteRequest, _ func(analysisruntime.WorkerEvent)) (analysisruntime.ExecuteResult, error) {
	f.request = request
	if f.fail {
		if _, err := f.conversations.FailTurn(ctx, conversation.FailTurnRequest{
			TurnID: request.TurnID, CodeSnapshot: request.Code, ErrorMessage: "boom",
		}); err != nil {
			return analysisruntime.ExecuteResult{}, err
		}
		return analysisruntime.ExecuteResult{Success: false, Error: "boom", RunID: "run-1"}, nil
	}
	if _, err := f.conversations.CompleteTurn(ctx, conversation.CompleteTurnRequest{
		TurnID: request.TurnID, CodeSnapshot: request.Code, ResultJSON: "42", ResultKind: "scalar",
	}); err != nil {
		return analysisruntime.ExecuteResult{}, err
	}
	return analysisruntime.ExecuteResult{Success: true, Result: json.RawMessage(`42`), ResultKind: "scalar", RunID: "run-1"}, nil
}

func appErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}

func TestManualRunCreatesPersistedChildExecutesAndMarksItFinal(t *testing.T) {
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
	defer workspaces.Close()
	conversationRepository, err := conversation.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	conversations := conversation.NewService(conversationRepository, conversation.NewFileHeap(filepath.Join(root, "workspaces")))
	defer conversations.Close()
	thread, _ := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: createdWorkspace.ID, Title: "Thread"})
	parent, _ := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{ConversationID: thread.ID, UserText: "Question"})
	parent, _ = conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{TurnID: parent.ID, AssistantText: "Answer"})
	_, _ = conversations.MarkFinalTurn(context.Background(), thread.ID, parent.ID)
	catalog := &fakeCatalog{}
	executor := &fakeExecutor{conversations: conversations}
	service := NewService(conversations, catalog, executor)
	result, err := service.Run(context.Background(), RunRequest{WorkspaceID: createdWorkspace.ID, ConversationID: thread.ID, ParentTurnID: &parent.ID, Code: "result = 42", TimeoutSeconds: 60}, nil)
	if err != nil || !result.Execution.Success || result.Turn.ParentTurnID == nil || *result.Turn.ParentTurnID != parent.ID || result.Turn.Status != conversation.TurnStatusCompleted {
		t.Fatalf("Run()=%#v,%v", result, err)
	}
	if catalog.calls != 1 || executor.request.TurnID != result.Turn.ID || executor.request.Code != "result = 42" {
		t.Fatalf("execution request=%#v catalog calls=%d", executor.request, catalog.calls)
	}
	stored, _ := conversations.GetConversation(context.Background(), thread.ID)
	if stored.FinalTurnID == nil || *stored.FinalTurnID != result.Turn.ID {
		t.Fatalf("final turn=%#v", stored.FinalTurnID)
	}
}

func TestManualRunCreatesConversationAndValidatesOwnership(t *testing.T) {
	root := t.TempDir()
	database := filepath.Join(root, "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	workspaces := workspace.NewService(workspaceRepository)
	first, _ := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "First"})
	second, _ := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "Second"})
	defer workspaces.Close()

	conversationRepository, err := conversation.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	conversations := conversation.NewService(conversationRepository, conversation.NewFileHeap(filepath.Join(root, "workspaces")))
	defer conversations.Close()
	existing, _ := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: first.ID, Title: "Existing"})
	service := NewService(conversations, &fakeCatalog{}, &fakeExecutor{conversations: conversations})

	if _, err := service.Run(context.Background(), RunRequest{WorkspaceID: second.ID, ConversationID: existing.ID, Code: "1", TimeoutSeconds: 60}, nil); appErrorCode(err) != "conversation_workspace_mismatch" {
		t.Fatalf("workspace mismatch error = %v", err)
	}
	created, err := service.Run(context.Background(), RunRequest{WorkspaceID: second.ID, Code: "2", TimeoutSeconds: 60}, nil)
	if err != nil || created.Conversation.ID == "" || created.Conversation.WorkspaceID != second.ID || created.Turn.ConversationID != created.Conversation.ID {
		t.Fatalf("new conversation run = %#v, %v", created, err)
	}
}

func TestManualRunRejectsInvalidInputBeforeCreatingPersistentState(t *testing.T) {
	catalog := &fakeCatalog{}
	service := NewService(nil, catalog, nil)
	for _, request := range []RunRequest{
		{WorkspaceID: "", Code: "1", TimeoutSeconds: 60},
		{WorkspaceID: "workspace", Code: " ", TimeoutSeconds: 60},
		{WorkspaceID: "workspace", Code: "1", TimeoutSeconds: 0},
		{WorkspaceID: "workspace", Code: "1", TimeoutSeconds: 3601},
	} {
		if _, err := service.Run(context.Background(), request, nil); err == nil {
			t.Fatalf("Run(%#v) did not fail", request)
		}
	}
	if catalog.calls != 0 {
		t.Fatalf("catalog calls = %d", catalog.calls)
	}
}

func TestFailedManualRunPersistsFailureWithoutMarkingItFinal(t *testing.T) {
	root := t.TempDir()
	database := filepath.Join(root, "inquira.db")
	workspaceRepository, _ := workspace.OpenSQLite(database)
	workspaces := workspace.NewService(workspaceRepository)
	createdWorkspace, _ := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "Analysis"})
	defer workspaces.Close()
	conversationRepository, _ := conversation.OpenSQLite(database)
	conversations := conversation.NewService(conversationRepository, conversation.NewFileHeap(filepath.Join(root, "workspaces")))
	defer conversations.Close()
	thread, _ := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: createdWorkspace.ID, Title: "Thread"})
	parent, _ := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{ConversationID: thread.ID, UserText: "Question"})
	parent, _ = conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{TurnID: parent.ID})
	_, _ = conversations.MarkFinalTurn(context.Background(), thread.ID, parent.ID)
	service := NewService(conversations, &fakeCatalog{}, &fakeExecutor{conversations: conversations, fail: true})

	result, err := service.Run(context.Background(), RunRequest{WorkspaceID: createdWorkspace.ID, ConversationID: thread.ID, ParentTurnID: &parent.ID, Code: "raise Exception()", TimeoutSeconds: 60}, nil)
	if err != nil || result.Execution.Success || result.Turn.Status != conversation.TurnStatusFailed {
		t.Fatalf("failed run = %#v, %v", result, err)
	}
	stored, _ := conversations.GetConversation(context.Background(), thread.ID)
	if stored.FinalTurnID != nil {
		t.Fatalf("failed turn became final: %#v", stored.FinalTurnID)
	}
}
