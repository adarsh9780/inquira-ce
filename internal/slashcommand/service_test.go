package slashcommand

import (
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"testing"

	"github.com/adarsh9780/inquira-ce/internal/analysisruntime"
	"github.com/adarsh9780/inquira-ce/internal/conversation"
	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
	"github.com/adarsh9780/inquira-ce/internal/workspace"
)

type fakeCatalog struct {
	result datacatalog.Catalog
	calls  int
}

func (f *fakeCatalog) Prepare(_ context.Context, workspaceID string) (datacatalog.Catalog, error) {
	f.calls++
	f.result.WorkspaceID = workspaceID
	return f.result, nil
}

type fakeCompiler struct {
	request CompileRequest
	result  CompiledCommand
	err     error
}

func (f *fakeCompiler) Compile(_ context.Context, request CompileRequest) (CompiledCommand, error) {
	f.request = request
	return f.result, f.err
}

type fakeExecutor struct {
	conversations *conversation.Service
	request       analysisruntime.ExecuteRequest
	result        analysisruntime.ExecuteResult
}

func (f *fakeExecutor) Execute(ctx context.Context, request analysisruntime.ExecuteRequest, _ func(analysisruntime.WorkerEvent)) (analysisruntime.ExecuteResult, error) {
	f.request = request
	if _, err := f.conversations.CompleteTurn(ctx, conversation.CompleteTurnRequest{
		TurnID: request.TurnID, AssistantText: request.AssistantText,
		CodeSnapshot: request.Code, MetadataJSON: request.MetadataJSON,
		ResultJSON: string(f.result.Result), ResultKind: f.result.ResultKind,
	}); err != nil {
		return analysisruntime.ExecuteResult{}, err
	}
	return f.result, nil
}

func newCommandHarness(t *testing.T) (*conversation.Service, workspace.Workspace, *fakeCatalog) {
	t.Helper()
	root := t.TempDir()
	database := filepath.Join(root, "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	workspaces := workspace.NewService(workspaceRepository)
	t.Cleanup(func() { _ = workspaces.Close() })
	created, err := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "Analysis"})
	if err != nil {
		t.Fatal(err)
	}
	conversationRepository, err := conversation.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	conversations := conversation.NewService(conversationRepository, conversation.NewFileHeap(filepath.Join(root, "workspaces")))
	t.Cleanup(func() { _ = conversations.Close() })
	catalog := &fakeCatalog{result: datacatalog.Catalog{Tables: []datacatalog.Table{{
		Name: "sales", Columns: nil,
	}}}}
	return conversations, created, catalog
}

func TestExecuteCompilesRunsAndPersistsNativeSlashCommand(t *testing.T) {
	conversations, ws, catalog := newCommandHarness(t)
	thread, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: ws.ID, Title: "Commands"})
	if err != nil {
		t.Fatal(err)
	}
	compiler := &fakeCompiler{result: CompiledCommand{
		Name: "shape", Output: "/shape executed for table 'sales'.", ResultType: "table",
		PythonCode: "_cmd_result = {'name': 'shape'}\n_cmd_result",
	}}
	workerPayload := json.RawMessage(`{"name":"shape","output":"/shape executed for table 'sales'.","result_type":"table","result":{"columns":["row_count"],"data":[{"row_count":3}],"row_count":1,"result_type":"table"},"truncated":false}`)
	executor := &fakeExecutor{conversations: conversations, result: analysisruntime.ExecuteResult{
		Success: true, Result: workerPayload, ResultKind: "object",
	}}
	service := NewService(conversations, catalog, compiler, executor)

	result, err := service.Execute(context.Background(), ExecuteRequest{
		WorkspaceID: ws.ID, ConversationID: thread.ID, Text: "/shape sales",
		DefaultTable: "sales", RowLimit: 500,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.Name != "shape" || result.ConversationID != thread.ID || result.TurnID == "" || result.ResultType != "table" {
		t.Fatalf("result = %#v", result)
	}
	if catalog.calls != 1 || compiler.request.Text != "/shape sales" || len(compiler.request.Columns) != 0 {
		t.Fatalf("compile request = %#v, catalog calls = %d", compiler.request, catalog.calls)
	}
	if executor.request.Code != compiler.result.PythonCode || executor.request.AssistantText != compiler.result.Output || !executor.request.UseResultOutput {
		t.Fatalf("execution request = %#v", executor.request)
	}
	turn, err := conversations.GetTurn(context.Background(), result.TurnID)
	if err != nil || turn.Status != conversation.TurnStatusCompleted || turn.UserText != "/shape sales" {
		t.Fatalf("turn = %#v, %v", turn, err)
	}
	stored, _ := conversations.GetConversation(context.Background(), thread.ID)
	if stored.FinalTurnID == nil || *stored.FinalTurnID != result.TurnID {
		t.Fatalf("final turn = %#v", stored.FinalTurnID)
	}
}

func TestExecuteCreatesConversationAndPassesCatalogColumns(t *testing.T) {
	conversations, ws, catalog := newCommandHarness(t)
	catalog.result.Tables[0].Columns = nil
	compiler := &fakeCompiler{result: CompiledCommand{
		Name: "help", Output: "Available slash commands.", ResultType: "table", PythonCode: "{'name': 'help'}",
	}}
	payload := json.RawMessage(`{"name":"help","output":"Available slash commands.","result_type":"table","result":null,"truncated":false}`)
	executor := &fakeExecutor{conversations: conversations, result: analysisruntime.ExecuteResult{Success: true, Result: payload, ResultKind: "object"}}
	service := NewService(conversations, catalog, compiler, executor)

	result, err := service.Execute(context.Background(), ExecuteRequest{WorkspaceID: ws.ID, Text: "/help", RowLimit: 500}, nil)
	if err != nil || result.ConversationID == "" {
		t.Fatalf("Execute() = %#v, %v", result, err)
	}
	thread, err := conversations.GetConversation(context.Background(), result.ConversationID)
	if err != nil || thread.Title != "/help" {
		t.Fatalf("conversation = %#v, %v", thread, err)
	}
}

func TestExecutePersistsCompilerFailureAndValidatesOwnership(t *testing.T) {
	conversations, ws, catalog := newCommandHarness(t)
	thread, _ := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: ws.ID, Title: "Commands"})
	compiler := &fakeCompiler{err: errors.New("Unknown command '/oops'.")}
	service := NewService(conversations, catalog, compiler, nil)

	_, err := service.Execute(context.Background(), ExecuteRequest{WorkspaceID: ws.ID, ConversationID: thread.ID, Text: "/oops", RowLimit: 500}, nil)
	if err == nil {
		t.Fatal("compiler failure was not returned")
	}
	turns, listErr := conversations.ListTurns(context.Background(), thread.ID)
	if listErr != nil || len(turns) != 1 || turns[0].Status != conversation.TurnStatusFailed {
		t.Fatalf("failed turns = %#v, %v", turns, listErr)
	}

	otherRepository, _ := workspace.OpenSQLite(filepath.Join(t.TempDir(), "other.db"))
	_ = otherRepository.Close()
	_, err = service.Execute(context.Background(), ExecuteRequest{WorkspaceID: "different", ConversationID: thread.ID, Text: "/help", RowLimit: 500}, nil)
	if err == nil {
		t.Fatal("workspace ownership mismatch was accepted")
	}
}
