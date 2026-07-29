package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/adarsh9780/inquira-ce/internal/analysisagent"
	"github.com/adarsh9780/inquira-ce/internal/analysisruntime"
	"github.com/adarsh9780/inquira-ce/internal/artifactbrowser"
	"github.com/adarsh9780/inquira-ce/internal/connection"
	"github.com/adarsh9780/inquira-ce/internal/conversation"
	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
	"github.com/adarsh9780/inquira-ce/internal/manualanalysis"
	"github.com/adarsh9780/inquira-ce/internal/modelconfig"
	"github.com/adarsh9780/inquira-ce/internal/runtimeprovision"
	"github.com/adarsh9780/inquira-ce/internal/slashcommand"
	workerruntime "github.com/adarsh9780/inquira-ce/internal/worker"
	"github.com/adarsh9780/inquira-ce/internal/workspace"
	dataworkerbundle "github.com/adarsh9780/inquira-ce/python/data_worker"
)

func TestProductionRuntimePipelineEndToEnd(t *testing.T) {
	if os.Getenv("INQUIRA_RUN_RUNTIME_E2E") != "1" {
		t.Skip("set INQUIRA_RUN_RUNTIME_E2E=1 to provision and exercise the bundled runtime")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	root := t.TempDir()
	runtimeRoot := filepath.Join(root, "runtime")
	workerProject := filepath.Join(runtimeRoot, "worker")
	if err := dataworkerbundle.Extract(workerProject); err != nil {
		t.Fatalf("extract bundled worker: %v", err)
	}
	pythonPath := strings.TrimSpace(os.Getenv("INQUIRA_E2E_PYTHON"))
	if pythonPath == "" {
		var err error
		pythonPath, err = exec.LookPath("python3")
		if err != nil {
			t.Fatal("Python 3.12 is required for the runtime integration test")
		}
	}
	pythonPath, err := filepath.Abs(pythonPath)
	if err != nil {
		t.Fatalf("resolve Python executable: %v", err)
	}
	provisioner := runtimeprovision.NewProvisioner(runtimeRoot)
	config := runtimeprovision.DefaultConfig()
	config.Mode = runtimeprovision.ModeExternalPython
	config.PythonExecutable = pythonPath
	provisioned, err := provisioner.Provision(ctx, config)
	if err != nil {
		t.Fatalf("provision bundled runtime: %v", err)
	}
	if !provisioner.Ready() || provisioned.PythonExecutable != provisioner.PythonExecutable() {
		t.Fatalf("runtime was not marked ready after verification: %+v", provisioner.Status())
	}

	modelServer := newRuntimeModelServer(t)
	defer modelServer.Close()
	transport := workerruntime.NewPersistentTransport(workerruntime.Config{
		PythonExecutable: provisioner.PythonExecutable(),
		WorkerSourceDir:  filepath.Join(workerProject, "src"),
		ReadinessCheck:   provisioner.Ready,
	})
	defer transport.Close()
	var ping struct {
		Status string `json:"status"`
	}
	if err := transport.Call(ctx, "ping", map[string]any{}, &ping); err != nil || ping.Status != "ready" {
		t.Fatalf("start persistent worker: ping=%+v err=%v", ping, err)
	}

	databasePath := filepath.Join(root, "inquira.db")
	models := runtimeE2EModels{configuration: modelconfig.RuntimeConfiguration{
		Provider: "openai", Model: "gpt-test", LiteModel: "gpt-test", CodingModel: "gpt-test",
		APIKey: "local-test-key", BaseURL: modelServer.URL + "/v1", MaxTokens: 4096,
		Temperature: 0, TopP: 1,
	}}
	workspaceRepository, err := workspace.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	workspaces := workspace.NewService(workspaceRepository).WithModelSource(models)
	defer workspaces.Close()
	createdWorkspace, err := workspaces.Create(ctx, workspace.CreateRequest{Name: "Runtime E2E", SchemaContext: "Sales reporting"})
	if err != nil {
		t.Fatal(err)
	}

	connectionRepository, err := connection.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	connections := connection.NewService(
		connectionRepository,
		connection.NewWorkerGateway(transport),
		filepath.Join(root, "snapshots"),
	)
	defer connections.Close()
	sourcePath := filepath.Join(root, "sales.csv")
	if err := os.WriteFile(sourcePath, []byte("region,amount\nNorth,10\nSouth,20\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	discovery, err := connections.Discover(ctx, connection.DiscoverRequest{AdapterKind: connection.AdapterCSV, SourcePath: sourcePath})
	if err != nil || len(discovery.Objects) != 1 {
		t.Fatalf("discover CSV: discovery=%+v err=%v", discovery, err)
	}
	preview, err := connections.Preview(ctx, connection.PreviewRequest{
		AdapterKind: connection.AdapterCSV, SourcePath: sourcePath,
		SourceObjectID: discovery.Objects[0].ID, Limit: 10,
	})
	if err != nil || len(preview.Rows) != 2 {
		t.Fatalf("preview CSV: preview=%+v err=%v", preview, err)
	}
	createdConnection, err := connections.Create(ctx, connection.CreateRequest{
		WorkspaceID: createdWorkspace.ID, Name: "Sales", AdapterKind: connection.AdapterCSV,
		SourcePath: sourcePath, SelectedObjectIDs: []string{discovery.Objects[0].ID},
	})
	if err != nil || createdConnection.Status != connection.StatusReady || len(createdConnection.Outputs) != 1 {
		t.Fatalf("materialize CSV: connection=%+v err=%v", createdConnection, err)
	}
	if info, statErr := os.Stat(createdConnection.Outputs[0].SnapshotPath); statErr != nil || !info.Mode().IsRegular() {
		t.Fatalf("snapshot was not published: %v", statErr)
	}

	catalogRepository, err := datacatalog.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	catalogs := datacatalog.NewService(
		workspaces, connections, datacatalog.NewWorkerGateway(transport), filepath.Join(root, "workspaces"),
	).WithSchemaRepository(catalogRepository)
	defer catalogs.Close()
	catalog, err := catalogs.Prepare(ctx, createdWorkspace.ID)
	if err != nil || len(catalog.Tables) != 1 || catalog.Tables[0].Name != "sales" {
		t.Fatalf("build DuckDB catalog: catalog=%+v err=%v", catalog, err)
	}

	conversationRepository, err := conversation.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	conversations := conversation.NewService(
		conversationRepository,
		conversation.NewFileHeap(filepath.Join(root, "workspaces")),
	)
	defer conversations.Close()
	runs := analysisruntime.NewService(
		conversations, analysisruntime.NewWorkerGateway(transport),
		filepath.Join(root, "workspaces"), filepath.Join(root, "execution-staging"),
	)
	manual := manualanalysis.NewService(conversations, catalogs, runs)
	manualResult, err := manual.Run(ctx, manualanalysis.RunRequest{
		WorkspaceID:    createdWorkspace.ID,
		Code:           "result = conn.sql(\"SELECT SUM(amount) AS total FROM sales\").df()\nresult",
		TimeoutSeconds: 30,
	}, nil)
	if err != nil || !manualResult.Execution.Success {
		t.Fatalf("execute through Jupyter: result=%+v err=%v", manualResult, err)
	}
	assertRuntimeTotal(t, manualResult.Execution.Result, 30)
	if len(manualResult.Execution.Artifacts) != 1 {
		t.Fatalf("manual artifacts = %+v", manualResult.Execution.Artifacts)
	}
	manualArtifactPath, err := conversations.ArtifactPath(ctx, manualResult.Execution.Artifacts[0].ID)
	if err != nil {
		t.Fatalf("resolve stored manual artifact: %v", err)
	}
	if _, err := os.Stat(manualArtifactPath); err != nil {
		t.Fatalf("stored manual artifact is unavailable: %v", err)
	}
	commands := slashcommand.NewService(
		conversations, catalogs, slashcommand.NewWorkerGateway(transport), runs,
	)
	commandResult, err := commands.Execute(ctx, slashcommand.ExecuteRequest{
		WorkspaceID: createdWorkspace.ID, Text: "/shape sales", RowLimit: 500,
	}, nil)
	if err != nil || commandResult.Name != "shape" || commandResult.ConversationID == "" || commandResult.TurnID == "" {
		t.Fatalf("execute native slash command: result=%+v err=%v", commandResult, err)
	}
	var shapeResult struct {
		Data []struct {
			RowCount int `json:"row_count"`
		} `json:"data"`
	}
	if err := json.Unmarshal(commandResult.Result, &shapeResult); err != nil || len(shapeResult.Data) != 1 || shapeResult.Data[0].RowCount != 2 {
		t.Fatalf("native slash command payload=%s err=%v", commandResult.Result, err)
	}

	agent := analysisagent.NewService(
		conversations, catalogs, workspaces, analysisagent.NewWorkerGateway(transport), runs,
	)
	events := make([]analysisruntime.WorkerEvent, 0)
	agentResult, err := agent.Analyze(ctx, analysisagent.AnalyzeRequest{
		WorkspaceID: createdWorkspace.ID, Question: "What are total sales?", TimeoutSeconds: 45,
	}, func(event analysisruntime.WorkerEvent) { events = append(events, event) })
	if err != nil || !agentResult.Execution.Success {
		t.Fatalf("run LangGraph analysis: result=%+v err=%v", agentResult, err)
	}
	if agentResult.Answer != "Total sales are 30." || agentResult.Turn.Status != conversation.TurnStatusCompleted {
		t.Fatalf("unexpected persisted agent result: %+v", agentResult)
	}
	assertRuntimeTotal(t, agentResult.Execution.Result, 30)
	if len(agentResult.Artifacts) != 1 || !hasRuntimeEvent(events, "agent_status") {
		t.Fatalf("agent artifacts/events: artifacts=%+v events=%+v", agentResult.Artifacts, events)
	}
	if modelServer.RequestCount() < 3 {
		t.Fatalf("agent did not exercise the provider path; requests=%d", modelServer.RequestCount())
	}

	if err := transport.Close(); err != nil {
		t.Fatalf("stop first worker: %v", err)
	}
	restarted := workerruntime.NewPersistentTransport(workerruntime.Config{
		PythonExecutable: provisioner.PythonExecutable(), WorkerSourceDir: filepath.Join(workerProject, "src"),
		ReadinessCheck: provisioner.Ready,
	})
	defer restarted.Close()
	browser := artifactbrowser.NewService(conversations, artifactbrowser.NewWorkerGateway(restarted))
	rows, err := browser.RowsForWorkspace(ctx, createdWorkspace.ID, agentResult.Artifacts[0].ID, artifactbrowser.RowsRequest{Limit: 10})
	if err != nil || len(rows.Rows) != 1 {
		t.Fatalf("read persisted artifact after worker restart: rows=%+v err=%v", rows, err)
	}
}

type runtimeE2EModels struct {
	configuration modelconfig.RuntimeConfiguration
}

func (m runtimeE2EModels) GetPreferences(context.Context, string) (modelconfig.PreferencesResponse, error) {
	return modelconfig.PreferencesResponse{
		LLMProvider: "openai", AvailableProviders: []string{"openai"},
		SelectedModel: "gpt-test", SelectedLiteModel: "gpt-test", SelectedCodingModel: "gpt-test",
		SelectedProviderAPIKeyPresent: true,
		ProviderModelCatalogs: map[string]modelconfig.Catalog{
			"openai": {MainModels: []string{"gpt-test"}, LiteModels: []string{"gpt-test"}},
		},
	}, nil
}

func (m runtimeE2EModels) RuntimeConfigurationFor(_ context.Context, overrides modelconfig.RuntimeOverrides, preferLite bool) (modelconfig.RuntimeConfiguration, error) {
	configuration := m.configuration
	if preferLite && configuration.LiteModel != "" {
		configuration.Model = configuration.LiteModel
	}
	if overrides.AllowDataSamples != nil {
		configuration.AllowDataSamples = *overrides.AllowDataSamples
	}
	return configuration, nil
}

type runtimeModelServer struct {
	*httptest.Server
	mu       sync.Mutex
	requests int
}

func newRuntimeModelServer(t *testing.T) *runtimeModelServer {
	t.Helper()
	server := &runtimeModelServer{}
	server.Server = httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		server.mu.Lock()
		server.requests++
		server.mu.Unlock()
		defer request.Body.Close()
		var payload map[string]any
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			http.Error(writer, err.Error(), http.StatusBadRequest)
			return
		}
		name := runtimeSchemaName(payload)
		value := runtimeModelValue(name)
		content, _ := json.Marshal(value)
		writer.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(writer).Encode(map[string]any{
			"id": "chatcmpl-runtime-e2e", "object": "chat.completion", "created": 0, "model": "gpt-test",
			"choices": []any{map[string]any{
				"index": 0, "finish_reason": "stop",
				"message": map[string]any{"role": "assistant", "content": string(content)},
			}},
			"usage": map[string]any{"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
		})
	}))
	return server
}

func (s *runtimeModelServer) RequestCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.requests
}

func runtimeSchemaName(payload map[string]any) string {
	responseFormat, _ := payload["response_format"].(map[string]any)
	jsonSchema, _ := responseFormat["json_schema"].(map[string]any)
	name, _ := jsonSchema["name"].(string)
	return name
}

func runtimeModelValue(name string) map[string]any {
	switch name {
	case "RouteDecision":
		return map[string]any{"route": "analysis", "reasoning": "The question requires a calculation.", "progress_message": "I will analyze sales."}
	case "ContextEnrichmentPlan":
		return map[string]any{"enough_context": true, "missing_context": []any{}, "notes": "Sales and amount are available.", "progress_message": "I found the required fields.", "tools": []any{}}
	case "AnalysisOutput":
		return map[string]any{
			"code":        "result = conn.sql('SELECT SUM(amount) AS total FROM sales').df()",
			"explanation": "Sum the amount column.", "progress_message": "I prepared the calculation.",
			"output_contract":       []any{map[string]any{"name": "result", "kind": "dataframe", "description": "Total sales"}},
			"search_schema_queries": []any{}, "selected_tables": []any{"sales"}, "join_keys": []any{}, "joins_used": false,
		}
	case "ResultExplanation":
		return map[string]any{"result_explanation": "Total sales are 30.", "code_explanation": "The query summed amount.", "progress_message": "I summarized the result."}
	default:
		return map[string]any{"answer": "Total sales are 30.", "progress_message": "I answered the question."}
	}
}

func assertRuntimeTotal(t *testing.T, payload json.RawMessage, expected float64) {
	t.Helper()
	var result struct {
		Rows []map[string]any `json:"rows"`
	}
	if err := json.Unmarshal(payload, &result); err != nil || len(result.Rows) != 1 {
		t.Fatalf("result payload = %s err=%v", payload, err)
	}
	value, ok := result.Rows[0]["total"].(float64)
	if !ok || value != expected {
		t.Fatalf("total = %v, want %v", result.Rows[0]["total"], expected)
	}
}

func hasRuntimeEvent(events []analysisruntime.WorkerEvent, eventType string) bool {
	for _, event := range events {
		if event.Type == eventType {
			return true
		}
	}
	return false
}
