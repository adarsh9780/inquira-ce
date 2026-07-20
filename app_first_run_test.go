package main

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"inquira-go/internal/analysisagent"
	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/connection"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
	"inquira-go/internal/workspace"
)

func TestNativeFirstRunJourneyReachesFirstAnalysis(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	databasePath := filepath.Join(root, "inquira.db")
	secrets := &memorySecretStore{values: map[string]string{}}

	modelRepository, err := modelconfig.OpenSQLite(databasePath)
	if err != nil {
		t.Fatalf("open model repository: %v", err)
	}
	models := modelconfig.NewService(modelRepository, secrets, staticModelHTTPClient{})
	t.Cleanup(func() { _ = models.Close() })

	workspaceRepository, err := workspace.OpenSQLite(databasePath)
	if err != nil {
		t.Fatalf("open workspace repository: %v", err)
	}
	workspaces := workspace.NewService(workspaceRepository).WithModelSource(models)
	t.Cleanup(func() { _ = workspaces.Close() })

	connectionRepository, err := connection.OpenSQLite(databasePath)
	if err != nil {
		t.Fatalf("open connection repository: %v", err)
	}
	connections := connection.NewService(
		connectionRepository,
		firstRunAdapter{},
		filepath.Join(root, "snapshots"),
	)
	t.Cleanup(func() { _ = connections.Close() })

	conversationRepository, err := conversation.OpenSQLite(databasePath)
	if err != nil {
		t.Fatalf("open conversation repository: %v", err)
	}
	conversations := conversation.NewService(
		conversationRepository,
		conversation.NewFileHeap(filepath.Join(root, "heap")),
	)
	t.Cleanup(func() { _ = conversations.Close() })

	runs := analysisruntime.NewService(
		conversations,
		unusedKernel{},
		filepath.Join(root, "workspace-runtime"),
		filepath.Join(root, "staging"),
	)
	catalog := firstRunCatalog{databasePath: filepath.Join(root, "workspace.duckdb")}
	agent := &recordingAgent{}
	analysis := analysisagent.NewService(conversations, catalog, workspaces, agent, runs)
	app := &App{
		models: models, workspaces: workspaces, connections: connections,
		conversations: conversations, analysis: runs, agent: analysis,
	}

	apiKey := "company-managed-secret"
	preferences, err := app.SaveProviderConfiguration(modelconfig.SaveRequest{
		Provider: "openai",
		APIKey:   &apiKey,
	})
	if err != nil {
		t.Fatalf("save model connection: %v", err)
	}
	if !preferences.SelectedProviderAPIKeyPresent {
		t.Fatal("expected the model connection to be ready")
	}
	serialized, err := json.Marshal(preferences)
	if err != nil {
		t.Fatalf("marshal public preferences: %v", err)
	}
	if strings.Contains(string(serialized), apiKey) {
		t.Fatal("model credential leaked through the public application response")
	}
	status, err := app.CompleteModelOnboarding()
	if err != nil || !status.Completed || !status.ConnectionReady {
		t.Fatalf("complete model onboarding: status=%+v err=%v", status, err)
	}

	createdWorkspace, err := app.CreateWorkspace(workspace.CreateRequest{Name: "First analysis"})
	if err != nil {
		t.Fatalf("create workspace: %v", err)
	}
	initialAI, err := app.GetWorkspaceAIConfig(createdWorkspace.ID)
	if err != nil {
		t.Fatalf("get workspace AI configuration: %v", err)
	}
	if initialAI.Readiness.ConfigurationReviewed {
		t.Fatal("new workspace must require an explicit AI and privacy review")
	}
	reviewedAI, err := app.UpdateWorkspaceAIConfig(createdWorkspace.ID, workspace.AIConfigUpdateRequest{
		AllowLLMDataSamples: false,
	})
	if err != nil {
		t.Fatalf("review workspace AI configuration: %v", err)
	}
	if !reviewedAI.Readiness.Ready || reviewedAI.Effective.AllowLLMDataSamples {
		t.Fatalf("workspace AI review was not applied: %+v", reviewedAI)
	}

	sourcePath := filepath.Join(root, "sales.csv")
	if err := os.WriteFile(sourcePath, []byte("amount\n42\n"), 0o600); err != nil {
		t.Fatalf("write source fixture: %v", err)
	}
	discovery, err := app.DiscoverLocalConnection(connection.DiscoverRequest{
		AdapterKind: connection.AdapterCSV,
		SourcePath:  sourcePath,
	})
	if err != nil || len(discovery.Objects) != 1 {
		t.Fatalf("discover local connection: discovery=%+v err=%v", discovery, err)
	}
	preview, err := app.PreviewLocalConnection(connection.PreviewRequest{
		AdapterKind:    connection.AdapterCSV,
		SourcePath:     sourcePath,
		SourceObjectID: discovery.Objects[0].ID,
		Limit:          10,
	})
	if err != nil || len(preview.Rows) != 1 {
		t.Fatalf("preview local connection: preview=%+v err=%v", preview, err)
	}
	createdConnection, err := app.CreateLocalConnection(connection.CreateRequest{
		WorkspaceID:       createdWorkspace.ID,
		Name:              "Sales",
		AdapterKind:       connection.AdapterCSV,
		SourcePath:        sourcePath,
		SelectedObjectIDs: []string{discovery.Objects[0].ID},
	})
	if err != nil {
		t.Fatalf("create local connection: %v", err)
	}
	if createdConnection.Status != connection.StatusReady || len(createdConnection.Outputs) != 1 {
		t.Fatalf("connection snapshot is not ready: %+v", createdConnection)
	}

	result, err := app.AnalyzeQuestion(analysisagent.AnalyzeRequest{
		WorkspaceID:    createdWorkspace.ID,
		Question:       "What is total sales?",
		TimeoutSeconds: 30,
	})
	if err != nil {
		t.Fatalf("run first analysis: %v", err)
	}
	if result.Answer != "Total sales are 42." || result.Conversation.ID == "" || result.Turn.ID == "" {
		t.Fatalf("unexpected first analysis result: %+v", result)
	}
	if agent.request.Model.Provider != "openai" || agent.request.Model.APIKey != apiKey {
		t.Fatalf("agent did not receive the configured runtime model: %+v", agent.request.Model)
	}
	if agent.request.WorkspaceID != createdWorkspace.ID || agent.request.DatabasePath != catalog.databasePath {
		t.Fatalf("agent received the wrong workspace catalog: %+v", agent.request)
	}
}

type memorySecretStore struct {
	mu     sync.Mutex
	values map[string]string
}

func (s *memorySecretStore) Set(provider, secret string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.values[provider] = secret
	return nil
}

func (s *memorySecretStore) Get(provider string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.values[provider], nil
}

func (s *memorySecretStore) Delete(provider string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.values, provider)
	return nil
}

func (s *memorySecretStore) Has(provider string) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.values[provider] != "", nil
}

type staticModelHTTPClient struct{}

func (staticModelHTTPClient) Do(*http.Request) (*http.Response, error) {
	return &http.Response{
		StatusCode: http.StatusOK,
		Header:     make(http.Header),
		Body:       io.NopCloser(strings.NewReader(`{"data":[{"id":"gpt-4.1"},{"id":"gpt-4.1-mini"}]}`)),
	}, nil
}

type firstRunAdapter struct{}

func (firstRunAdapter) Discover(_ context.Context, request connection.AdapterRequest) (connection.Discovery, error) {
	return connection.Discovery{
		AdapterKind: request.AdapterKind,
		SourcePath:  request.SourcePath,
		Fingerprint: "source-v1",
		Objects: []connection.SourceObject{{
			ID: "file", Name: "sales", Kind: "table",
			Columns: []connection.Column{{Name: "amount", DataType: "BIGINT"}},
		}},
	}, nil
}

func (firstRunAdapter) Preview(_ context.Context, _ connection.AdapterRequest, _ int) (connection.Preview, error) {
	return connection.Preview{
		Columns: []connection.Column{{Name: "amount", DataType: "BIGINT"}},
		Rows:    []map[string]any{{"amount": int64(42)}},
	}, nil
}

func (firstRunAdapter) Materialize(_ context.Context, request connection.MaterializeRequest) (connection.Materialization, error) {
	if err := os.MkdirAll(request.TargetDir, 0o700); err != nil {
		return connection.Materialization{}, err
	}
	const relativePath = "sales.parquet"
	if err := os.WriteFile(filepath.Join(request.TargetDir, relativePath), []byte("PAR1"), 0o600); err != nil {
		return connection.Materialization{}, err
	}
	return connection.Materialization{
		Fingerprint: "source-v1",
		Outputs: []connection.MaterializedOutput{{
			SourceObjectID: request.SelectedObjectIDs[0], Name: "sales",
			RelativePath: relativePath, Format: "parquet",
			Columns:  []connection.Column{{Name: "amount", DataType: "BIGINT"}},
			RowCount: 1, ByteSize: 4,
		}},
	}, nil
}

type firstRunCatalog struct{ databasePath string }

func (c firstRunCatalog) Prepare(_ context.Context, workspaceID string) (datacatalog.Catalog, error) {
	return datacatalog.Catalog{
		WorkspaceID:  workspaceID,
		DatabasePath: c.databasePath,
		AnalysisSchema: datacatalog.AnalysisSchema{Tables: []datacatalog.AnalysisTable{{
			Name:    "sales",
			Columns: []datacatalog.SchemaColumn{{Name: "amount", DataType: "BIGINT"}},
		}}},
	}, nil
}

type recordingAgent struct {
	request analysisagent.AgentWorkerRequest
}

func (a *recordingAgent) Analyze(_ context.Context, request analysisagent.AgentWorkerRequest, _ func(analysisruntime.WorkerEvent)) (analysisagent.AgentWorkerResult, error) {
	a.request = request
	return analysisagent.AgentWorkerResult{
		Success: true,
		Answer:  "Total sales are 42.",
		Code:    "result = 42",
		Route:   "analysis",
		Execution: analysisruntime.ExecuteWorkerResult{
			Success:    true,
			Result:     json.RawMessage(`{"total":42}`),
			ResultKind: "scalar",
		},
	}, nil
}

func (*recordingAgent) Cancel(context.Context, string) (bool, error) { return true, nil }

type unusedKernel struct{}

func (unusedKernel) Execute(context.Context, analysisruntime.ExecuteWorkerRequest, func(analysisruntime.WorkerEvent)) (analysisruntime.ExecuteWorkerResult, error) {
	panic("kernel execution is not part of the agent first-run contract")
}

func (unusedKernel) Status(context.Context, string) (analysisruntime.KernelStatus, error) {
	return analysisruntime.KernelStatus{}, nil
}

func (unusedKernel) Reset(context.Context, string) (bool, error) { return false, nil }

func (unusedKernel) Interrupt(context.Context, string) (bool, error) { return false, nil }
