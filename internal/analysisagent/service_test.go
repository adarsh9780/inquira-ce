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
	config      modelconfig.RuntimeConfiguration
	err         error
	workspaceID string
}

func (f *fakeModelSource) RuntimeConfiguration(_ context.Context, workspaceID string) (modelconfig.RuntimeConfiguration, error) {
	f.workspaceID = workspaceID
	return f.config, f.err
}

type fakeAgentGateway struct {
	request         AgentWorkerRequest
	result          AgentWorkerResult
	err             error
	events          []analysisruntime.WorkerEvent
	cancelWorkspace string
	cancelRequestID string
	cancelled       bool
	cancelErr       error
	intervention    InterventionResponse
	interventionErr error
}

func (f *fakeAgentGateway) Cancel(_ context.Context, workspaceID, clientRequestID string) (bool, error) {
	f.cancelWorkspace = workspaceID
	f.cancelRequestID = clientRequestID
	return f.cancelled, f.cancelErr
}

func (f *fakeAgentGateway) RespondIntervention(_ context.Context, interventionID string, selected []string) (InterventionResponse, error) {
	if f.intervention.InterventionID == "" {
		f.intervention = InterventionResponse{InterventionID: interventionID, Accepted: len(selected) > 0}
	}
	return f.intervention, f.interventionErr
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
		&fakeCatalogSource{catalog: datacatalog.Catalog{
			WorkspaceID: createdWorkspace.ID, DatabasePath: catalogPath,
			AnalysisSchema: datacatalog.AnalysisSchema{Context: "Revenue reporting", Tables: []datacatalog.AnalysisTable{{
				Name: "sales", Columns: []datacatalog.SchemaColumn{{Name: "amount", DataType: "DOUBLE", Description: "Booked revenue", Aliases: []string{"sales"}}},
			}}},
		}},
		&fakeModelSource{config: modelconfig.RuntimeConfiguration{Provider: "openai", Model: "gpt-4o", APIKey: "runtime-secret"}},
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
			Route: "analysis", Metadata: map[string]any{
				"token_usage": map[string]any{"input_tokens": 20, "output_tokens": 5, "total_tokens": 25},
			},
			Execution: analysisruntime.ExecuteWorkerResult{
				Success: true, Result: executionResult, ResultKind: "dataframe",
				Artifacts: []analysisruntime.ArtifactCandidate{{Kind: "dataframe", SourcePath: "/staging/data.parquet"}},
			},
		},
		events: []analysisruntime.WorkerEvent{{Type: "agent_status", Data: map[string]any{"stage": "executing"}}},
	}
	service, conversations, workspaceID, runs := newAgentService(t, gateway)
	events := make([]analysisruntime.WorkerEvent, 0)
	result, err := service.Analyze(context.Background(), AnalyzeRequest{
		ClientRequestID: "request-1", WorkspaceID: workspaceID, Question: "What are total sales?", CurrentCode: "result = previous", TimeoutSeconds: 30,
		Attachments: []ImageAttachment{{
			AttachmentID: "image-1", MediaType: "image/png", Filename: "chart.png", DataBase64: "aW1hZ2U=",
		}},
	}, func(event analysisruntime.WorkerEvent) { events = append(events, event) })
	if err != nil {
		t.Fatal(err)
	}
	if result.Conversation.ID == "" || result.Turn.ID == "" || result.Answer != gateway.result.Answer || !result.Execution.Success || result.Route != "analysis" {
		t.Fatalf("result = %#v", result)
	}
	if gateway.request.ClientRequestID != "request-1" || gateway.request.Model.APIKey != "runtime-secret" || gateway.request.DatabasePath == "" || gateway.request.RunID != "run-1" {
		t.Fatalf("worker request = %#v", gateway.request)
	}
	if len(events) != 1 || events[0].ClientRequestID != "request-1" || events[0].WorkspaceID != workspaceID ||
		events[0].ConversationID != result.Conversation.ID || events[0].TurnID != result.Turn.ID || events[0].RunID != "run-1" {
		t.Fatalf("scoped events = %#v", events)
	}
	if service.models.(*fakeModelSource).workspaceID != workspaceID {
		t.Fatalf("model configuration workspace = %q", service.models.(*fakeModelSource).workspaceID)
	}
	if gateway.request.ConversationID != result.Conversation.ID || gateway.request.TurnID != result.Turn.ID ||
		gateway.request.CurrentCode != "result = previous" || len(gateway.request.Attachments) != 1 || gateway.request.Attachments[0].AttachmentID != "image-1" {
		t.Fatalf("worker identity/attachments = %#v", gateway.request)
	}
	if gateway.request.Schema.Context != "Revenue reporting" || gateway.request.Schema.Tables[0].Columns[0].Description != "Booked revenue" {
		t.Fatalf("semantic schema = %#v", gateway.request.Schema)
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
		turn.ResultJSON != string(executionResult) || !strings.Contains(turn.MetadataJSON, `"total_tokens":25`) ||
		!strings.Contains(turn.MetadataJSON, `"user_attachments"`) || !strings.Contains(turn.MetadataJSON, `"attachment_id":"image-1"`) ||
		strings.Contains(string(encoded), "runtime-secret") {
		t.Fatalf("persisted turn = %s", encoded)
	}
}

func TestAnalyzeRejectsInvalidImageAttachments(t *testing.T) {
	service, _, workspaceID, _ := newAgentService(t, &fakeAgentGateway{})
	tests := []AnalyzeRequest{
		{WorkspaceID: workspaceID, Question: "Q", TimeoutSeconds: 30, Attachments: []ImageAttachment{{AttachmentID: "x", MediaType: "text/plain", Filename: "x.txt", DataBase64: "eA=="}}},
		{WorkspaceID: workspaceID, Question: "Q", TimeoutSeconds: 30, Attachments: []ImageAttachment{{AttachmentID: "x", MediaType: "image/png", Filename: "x.png", DataBase64: "not-base64"}}},
	}
	for _, request := range tests {
		if _, err := service.Analyze(context.Background(), request, nil); appErrorCode(err) != "agent_attachments_invalid" {
			t.Fatalf("error = %v", err)
		}
	}
}

func TestAnalyzeRejectsImagesForTextOnlyModel(t *testing.T) {
	service, _, workspaceID, _ := newAgentService(t, &fakeAgentGateway{})
	service.models = &fakeModelSource{config: modelconfig.RuntimeConfiguration{
		Provider: "ollama", Model: "qwen2.5-coder:7b",
	}}
	_, err := service.Analyze(context.Background(), AnalyzeRequest{
		WorkspaceID: workspaceID, Question: "Read this image", TimeoutSeconds: 30,
		Attachments: []ImageAttachment{{
			AttachmentID: "image-1", MediaType: "image/png", Filename: "chart.png", DataBase64: "aW1hZ2U=",
		}},
	}, nil)
	if appErrorCode(err) != "model_images_unsupported" {
		t.Fatalf("error = %v", err)
	}
}

func TestCancelValidatesWorkspaceAndDelegatesToWorker(t *testing.T) {
	gateway := &fakeAgentGateway{cancelled: true}
	service, _, _, _ := newAgentService(t, gateway)
	cancelled, err := service.Cancel(context.Background(), " workspace-1 ", " request-1 ")
	if err != nil || !cancelled || gateway.cancelWorkspace != "workspace-1" || gateway.cancelRequestID != "request-1" {
		t.Fatalf("cancelled=%v workspace=%q request=%q error=%v", cancelled, gateway.cancelWorkspace, gateway.cancelRequestID, err)
	}
	if _, err := service.Cancel(context.Background(), " ", "request-1"); appErrorCode(err) != "workspace_required" {
		t.Fatalf("blank workspace error = %v", err)
	}
	if _, err := service.Cancel(context.Background(), "workspace-1", " "); appErrorCode(err) != "agent_request_required" {
		t.Fatalf("blank request error = %v", err)
	}
	gateway.cancelErr = errors.New("worker unavailable")
	if _, err := service.Cancel(context.Background(), "workspace-1", "request-1"); appErrorCode(err) != "agent_cancel_failed" {
		t.Fatalf("worker error = %v", err)
	}
}

func TestRespondInterventionValidatesAndDelegatesToWorker(t *testing.T) {
	gateway := &fakeAgentGateway{}
	service, _, _, _ := newAgentService(t, gateway)
	response, err := service.RespondIntervention(context.Background(), " intervention-1 ", []string{" approve "})
	if err != nil || !response.Accepted || response.InterventionID != "intervention-1" {
		t.Fatalf("response=%#v error=%v", response, err)
	}
	if _, err := service.RespondIntervention(context.Background(), "", nil); appErrorCode(err) != "intervention_required" {
		t.Fatalf("blank intervention error = %v", err)
	}
	if _, err := service.RespondIntervention(context.Background(), "intervention-1", make([]string, 21)); appErrorCode(err) != "intervention_selection_invalid" {
		t.Fatalf("oversized selection error = %v", err)
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

func TestAnalyzeSendsOnlySelectedBranchContextAndSafeArtifactMetadata(t *testing.T) {
	gateway := &fakeAgentGateway{result: AgentWorkerResult{
		Success: true, Answer: "West remains the largest region.", Code: "result = conn.sql('select 1').df()",
		Execution: analysisruntime.ExecuteWorkerResult{Success: true, Result: json.RawMessage(`1`), ResultKind: "scalar"},
	}}
	service, conversations, workspaceID, _ := newAgentService(t, gateway)
	created, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: workspaceID, Title: "Regional sales"})
	if err != nil {
		t.Fatal(err)
	}
	root, err := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{
		ConversationID: created.ID, UserText: "Which region has the most sales?",
	})
	if err != nil {
		t.Fatal(err)
	}
	root, err = conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{
		TurnID: root.ID, AssistantText: "West has the most sales.", CodeSnapshot: "result = sales_by_region",
		ResultKind: "dataframe", ResultJSON: `{"columns":["region","sales"],"rows":[{"region":"West","sales":42}]}`,
	})
	if err != nil {
		t.Fatal(err)
	}
	artifact, err := conversations.PublishArtifact(context.Background(), conversation.PublishArtifactRequest{
		ConversationID: created.ID, TurnID: root.ID, Kind: "dataframe", LogicalName: "sales_by_region",
		DisplayName: "Sales by region", PayloadFormat: "parquet", MediaType: "application/vnd.apache.parquet",
	}, strings.NewReader("PAR1-history"))
	if err != nil {
		t.Fatal(err)
	}
	child, err := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{
		ConversationID: created.ID, ParentTurnID: &root.ID, UserText: "How much did West sell?",
	})
	if err != nil {
		t.Fatal(err)
	}
	child, err = conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{
		TurnID: child.ID, AssistantText: "West sold 42.", ResultKind: "scalar", ResultJSON: `42`,
	})
	if err != nil {
		t.Fatal(err)
	}
	sibling, err := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{
		ConversationID: created.ID, ParentTurnID: &root.ID, UserText: "Ignore West and discuss East.",
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{
		TurnID: sibling.ID, AssistantText: "East branch answer.", ResultKind: "scalar", ResultJSON: `18`,
	}); err != nil {
		t.Fatal(err)
	}

	result, err := service.Analyze(context.Background(), AnalyzeRequest{
		WorkspaceID: workspaceID, ConversationID: created.ID, ParentTurnID: &child.ID,
		Question: "Is it still the largest?", TimeoutSeconds: 30,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(gateway.request.Context.Turns) != 2 {
		t.Fatalf("context = %#v", gateway.request.Context)
	}
	if gateway.request.Context.Turns[0].TurnID != root.ID || gateway.request.Context.Turns[1].TurnID != child.ID {
		t.Fatalf("context order = %#v", gateway.request.Context.Turns)
	}
	encoded, _ := json.Marshal(gateway.request.Context)
	if strings.Contains(string(encoded), "East branch") || strings.Contains(string(encoded), "West\",\"sales\":42") || strings.Contains(string(encoded), artifact.RelativePath) {
		t.Fatalf("context leaked sibling, row samples, or storage path: %s", encoded)
	}
	if len(gateway.request.Context.Turns[0].Artifacts) != 1 || gateway.request.Context.Turns[0].Artifacts[0].LogicalName != "sales_by_region" {
		t.Fatalf("artifact context = %#v", gateway.request.Context.Turns[0].Artifacts)
	}
	persisted, err := conversations.GetTurn(context.Background(), result.Turn.ID)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(persisted.MetadataJSON, root.ID) || !strings.Contains(persisted.MetadataJSON, child.ID) || strings.Contains(persisted.MetadataJSON, "runtime-secret") {
		t.Fatalf("context references were not persisted safely: %s", persisted.MetadataJSON)
	}
}

func TestAnalyzeIncludesHistoricalResultSamplesOnlyWhenEnabled(t *testing.T) {
	gateway := &fakeAgentGateway{result: AgentWorkerResult{
		Success: true, Answer: "Answer", Code: "result = 1",
		Execution: analysisruntime.ExecuteWorkerResult{Success: true, Result: json.RawMessage(`1`), ResultKind: "scalar"},
	}}
	service, conversations, workspaceID, _ := newAgentService(t, gateway)
	service.models = &fakeModelSource{config: modelconfig.RuntimeConfiguration{
		Provider: "openai", Model: "gpt-test", APIKey: "runtime-secret", AllowDataSamples: true,
	}}
	created, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: workspaceID, Title: "Samples"})
	if err != nil {
		t.Fatal(err)
	}
	root, err := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{ConversationID: created.ID, UserText: "Show sales"})
	if err != nil {
		t.Fatal(err)
	}
	root, err = conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{
		TurnID: root.ID, AssistantText: "West sold 42.", ResultKind: "dataframe",
		ResultJSON: `{"columns":["region","sales"],"rows":[{"region":"West","sales":42}]}`,
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := service.Analyze(context.Background(), AnalyzeRequest{
		WorkspaceID: workspaceID, ConversationID: created.ID, ParentTurnID: &root.ID,
		Question: "Repeat that", TimeoutSeconds: 30,
	}, nil); err != nil {
		t.Fatal(err)
	}
	encoded, _ := json.Marshal(gateway.request.Context)
	if !strings.Contains(string(encoded), `West`) || !strings.Contains(string(encoded), `42`) {
		t.Fatalf("enabled historical samples missing: %s", encoded)
	}
}

func TestConversationContextKeepsTheMostRecentTwelveAncestors(t *testing.T) {
	service, conversations, workspaceID, _ := newAgentService(t, &fakeAgentGateway{})
	created, err := conversations.CreateConversation(context.Background(), conversation.CreateConversationRequest{WorkspaceID: workspaceID, Title: "Long branch"})
	if err != nil {
		t.Fatal(err)
	}
	turnIDs := make([]string, 0, 14)
	var parent *string
	for index := 0; index < 14; index++ {
		turn, err := conversations.CreateTurn(context.Background(), conversation.CreateTurnRequest{
			ConversationID: created.ID, ParentTurnID: parent, UserText: "Question",
		})
		if err != nil {
			t.Fatal(err)
		}
		turn, err = conversations.CompleteTurn(context.Background(), conversation.CompleteTurnRequest{
			TurnID: turn.ID, AssistantText: "Answer", ResultKind: "scalar", ResultJSON: `1`,
		})
		if err != nil {
			t.Fatal(err)
		}
		turnIDs = append(turnIDs, turn.ID)
		parent = &turn.ID
	}
	history, err := service.conversationContext(context.Background(), created.ID, parent, false)
	if err != nil {
		t.Fatal(err)
	}
	if len(history.Turns) != maxContextTurns || history.Turns[0].TurnID != turnIDs[2] || history.Turns[len(history.Turns)-1].TurnID != turnIDs[13] {
		t.Fatalf("bounded history = %#v", history.Turns)
	}
}

func appErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
