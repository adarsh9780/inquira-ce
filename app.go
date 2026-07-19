package main

import (
	"context"
	"path/filepath"

	"github.com/wailsapp/wails/v2/pkg/runtime"

	"inquira-go/internal/analysisagent"
	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/appdirs"
	"inquira-go/internal/apperror"
	"inquira-go/internal/artifactbrowser"
	"inquira-go/internal/connection"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/manualanalysis"
	"inquira-go/internal/modelconfig"
	"inquira-go/internal/netclient"
	"inquira-go/internal/runtimeprovision"
	"inquira-go/internal/schemageneration"
	workerruntime "inquira-go/internal/worker"
	"inquira-go/internal/workspace"
	dataworkerbundle "inquira-go/python/data_worker"
)

// App struct
type App struct {
	ctx           context.Context
	paths         appdirs.Paths
	provisioner   *runtimeprovision.Provisioner
	models        *modelconfig.Service
	workspaces    *workspace.Service
	connections   *connection.Service
	conversations *conversation.Service
	artifacts     *artifactbrowser.Service
	analysis      *analysisruntime.Service
	manual        *manualanalysis.Service
	schemas       *schemageneration.Service
	agent         *analysisagent.Service
	worker        *workerruntime.PersistentTransport
	catalog       *datacatalog.Service
	initErr       error
}

type RerunFinalResult struct {
	Conversation conversation.Conversation     `json:"conversation"`
	Turn         conversation.Turn             `json:"turn"`
	Answer       string                        `json:"answer"`
	Code         string                        `json:"code"`
	Execution    analysisruntime.ExecuteResult `json:"execution"`
	Artifacts    []conversation.Artifact       `json:"artifacts"`
}

// NewApp creates a new App application struct
func NewApp() *App {
	paths, err := appdirs.Resolve()
	if err != nil {
		return &App{initErr: err}
	}
	app := &App{paths: paths}
	if err := paths.Ensure(); err != nil {
		app.initErr = err
		return app
	}
	app.provisioner = runtimeprovision.NewProvisioner(paths.RuntimeDir)
	repository, err := modelconfig.OpenSQLite(paths.DatabasePath)
	if err != nil {
		app.initErr = err
		return app
	}
	httpClient, err := netclient.New(netclient.Config{})
	if err != nil {
		_ = repository.Close()
		app.initErr = err
		return app
	}
	app.models = modelconfig.NewService(repository, modelconfig.OSKeychain{}, httpClient)
	workspaceRepository, err := workspace.OpenSQLite(paths.DatabasePath)
	if err != nil {
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	app.workspaces = workspace.NewService(workspaceRepository)
	workerProject := filepath.Join(paths.RuntimeDir, "worker")
	if err := dataworkerbundle.Extract(workerProject); err != nil {
		_ = app.workspaces.Close()
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	connectionRepository, err := connection.OpenSQLite(paths.DatabasePath)
	if err != nil {
		_ = app.workspaces.Close()
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	transport := workerruntime.NewPersistentTransport(workerruntime.Config{
		PythonExecutable: app.provisioner.PythonExecutable(),
		WorkerSourceDir:  filepath.Join(workerProject, "src"),
		ReadinessCheck:   app.provisioner.Ready,
	})
	app.worker = transport
	app.connections = connection.NewService(
		connectionRepository, connection.NewWorkerGateway(transport), filepath.Join(paths.DataDir, "snapshots"),
	)
	catalogRepository, err := datacatalog.OpenSQLite(paths.DatabasePath)
	if err != nil {
		_ = app.worker.Close()
		_ = app.connections.Close()
		_ = app.workspaces.Close()
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	app.catalog = datacatalog.NewService(
		app.workspaces, app.connections, datacatalog.NewWorkerGateway(transport), filepath.Join(paths.DataDir, "workspaces"),
	).WithSchemaRepository(catalogRepository)
	app.schemas = schemageneration.NewService(
		app.catalog, app.models, schemageneration.NewWorkerGateway(transport),
	)
	conversationRepository, err := conversation.OpenSQLite(paths.DatabasePath)
	if err != nil {
		_ = app.worker.Close()
		_ = app.catalog.Close()
		_ = app.connections.Close()
		_ = app.workspaces.Close()
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	app.conversations = conversation.NewService(
		conversationRepository, conversation.NewFileHeap(filepath.Join(paths.DataDir, "workspaces")),
	)
	app.artifacts = artifactbrowser.NewService(app.conversations, artifactbrowser.NewWorkerGateway(transport))
	if _, err := app.conversations.ReconcileAll(context.Background()); err != nil {
		_ = app.worker.Close()
		_ = app.conversations.Close()
		_ = app.catalog.Close()
		_ = app.connections.Close()
		_ = app.workspaces.Close()
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	app.analysis = analysisruntime.NewService(
		app.conversations, analysisruntime.NewWorkerGateway(transport),
		filepath.Join(paths.DataDir, "workspaces"), filepath.Join(paths.DataDir, "execution-staging"),
	)
	app.manual = manualanalysis.NewService(app.conversations, app.catalog, app.analysis)
	app.agent = analysisagent.NewService(
		app.conversations, app.catalog, app.models, analysisagent.NewWorkerGateway(transport), app.analysis,
	)
	return app
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) shutdown(context.Context) {
	if a.worker != nil {
		_ = a.worker.Close()
	}
	if a.conversations != nil {
		_ = a.conversations.Close()
	}
	if a.catalog != nil {
		_ = a.catalog.Close()
	}
	if a.connections != nil {
		_ = a.connections.Close()
	}
	if a.workspaces != nil {
		_ = a.workspaces.Close()
	}
	if a.models != nil {
		_ = a.models.Close()
	}
}

func (a *App) analysisService() (*analysisruntime.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.analysis == nil {
		return nil, apperror.New("analysis_unavailable", "Python analysis is unavailable.")
	}
	return a.analysis, nil
}

func (a *App) manualAnalysisService() (*manualanalysis.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.manual == nil {
		return nil, apperror.New("manual_analysis_unavailable", "Manual Python analysis is unavailable.")
	}
	return a.manual, nil
}

func (a *App) agentService() (*analysisagent.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.agent == nil {
		return nil, apperror.New("agent_unavailable", "The analysis agent is unavailable.")
	}
	return a.agent, nil
}

func (a *App) conversationService() (*conversation.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.conversations == nil {
		return nil, apperror.New("conversation_unavailable", "Conversation storage is unavailable.")
	}
	return a.conversations, nil
}

func (a *App) artifactService() (*artifactbrowser.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.artifacts == nil {
		return nil, apperror.New("artifact_unavailable", "Artifact browsing is unavailable.")
	}
	return a.artifacts, nil
}

func (a *App) connectionService() (*connection.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	return a.connections, nil
}

func (a *App) catalogService() (*datacatalog.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.catalog == nil {
		return nil, apperror.New("catalog_unavailable", "Workspace analysis catalog is unavailable.")
	}
	return a.catalog, nil
}

func (a *App) schemaGenerationService() (*schemageneration.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.schemas == nil {
		return nil, apperror.New("schema_generation_unavailable", "AI schema generation is unavailable.")
	}
	return a.schemas, nil
}

func (a *App) workspaceService() (*workspace.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	return a.workspaces, nil
}

func (a *App) appContext() context.Context {
	if a.ctx != nil {
		return a.ctx
	}
	return context.Background()
}

func (a *App) modelService() (*modelconfig.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	return a.models, nil
}

// ApplicationPaths exposes the resolved local directories for diagnostics.
func (a *App) ApplicationPaths() appdirs.Paths { return a.paths }

func (a *App) GetModelPreferences(provider string) (modelconfig.PreferencesResponse, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.PreferencesResponse{}, err
	}
	return service.GetPreferences(a.appContext(), provider)
}

func (a *App) GetModelOnboardingStatus() (modelconfig.OnboardingStatus, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.OnboardingStatus{}, err
	}
	return service.GetOnboardingStatus(a.appContext())
}

func (a *App) CompleteModelOnboarding() (modelconfig.OnboardingStatus, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.OnboardingStatus{}, err
	}
	return service.CompleteOnboarding(a.appContext())
}

func (a *App) UpdateModelPreferences(request modelconfig.UpdateRequest) (modelconfig.PreferencesResponse, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.PreferencesResponse{}, err
	}
	return service.UpdatePreferences(a.appContext(), request)
}

func (a *App) VerifyProviderAPIKey(provider, apiKey string) (modelconfig.VerifyResponse, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.VerifyResponse{}, err
	}
	return service.VerifyKey(a.appContext(), provider, apiKey)
}

func (a *App) SaveProviderConfiguration(request modelconfig.SaveRequest) (modelconfig.PreferencesResponse, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.PreferencesResponse{}, err
	}
	return service.SaveConfiguration(a.appContext(), request)
}

func (a *App) RefreshProviderModels(request modelconfig.RefreshRequest) (modelconfig.PreferencesResponse, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.PreferencesResponse{}, err
	}
	return service.RefreshModels(a.appContext(), request)
}

func (a *App) SearchProviderModels(provider, query string, limit int) (modelconfig.SearchResponse, error) {
	service, err := a.modelService()
	if err != nil {
		return modelconfig.SearchResponse{}, err
	}
	return service.SearchModels(a.appContext(), provider, query, limit)
}

func (a *App) DeleteProviderAPIKey(provider string) (map[string]any, error) {
	service, err := a.modelService()
	if err != nil {
		return nil, err
	}
	return service.DeleteKey(a.appContext(), provider)
}

func (a *App) ListWorkspaces() (workspace.ListResponse, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.ListResponse{}, err
	}
	return service.List(a.appContext())
}

func (a *App) CreateWorkspace(request workspace.CreateRequest) (workspace.Workspace, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.Workspace{}, err
	}
	return service.Create(a.appContext(), request)
}

func (a *App) ActivateWorkspace(workspaceID string) (workspace.Workspace, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.Workspace{}, err
	}
	return service.Activate(a.appContext(), workspaceID)
}

func (a *App) UpdateWorkspace(request workspace.UpdateRequest) (workspace.Workspace, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.Workspace{}, err
	}
	return service.Update(a.appContext(), request)
}

func (a *App) GetWorkspaceSummary(workspaceID string) (workspace.Summary, error) {
	service, err := a.catalogService()
	if err != nil {
		return workspace.Summary{}, err
	}
	return service.SummarizeWorkspace(a.appContext(), workspaceID)
}

func (a *App) DeleteWorkspace(workspaceID string) (workspace.DeletionResult, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.DeletionResult{}, err
	}
	connectionService, err := a.connectionService()
	if err != nil {
		return workspace.DeletionResult{}, err
	}
	if a.worker != nil && a.worker.Running() && a.analysis != nil {
		_, _ = a.analysis.Reset(a.appContext(), workspaceID)
	}
	if catalogService, catalogErr := a.catalogService(); catalogErr != nil {
		return workspace.DeletionResult{}, catalogErr
	} else if catalogErr := catalogService.Remove(workspaceID); catalogErr != nil {
		return workspace.DeletionResult{}, catalogErr
	}
	if err := connectionService.DeleteWorkspaceConnections(a.appContext(), workspaceID); err != nil {
		return workspace.DeletionResult{}, err
	}
	return service.Delete(a.appContext(), workspaceID)
}

func (a *App) CreateConversation(request conversation.CreateConversationRequest) (conversation.Conversation, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Conversation{}, err
	}
	return service.CreateConversation(a.appContext(), request)
}

func (a *App) ListConversations(workspaceID string) ([]conversation.Conversation, error) {
	service, err := a.conversationService()
	if err != nil {
		return nil, err
	}
	return service.ListConversations(a.appContext(), workspaceID)
}

func (a *App) UpdateConversation(conversationID, title string) (conversation.Conversation, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Conversation{}, err
	}
	return service.UpdateConversation(a.appContext(), conversationID, title)
}

func (a *App) CreateConversationTurn(request conversation.CreateTurnRequest) (conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Turn{}, err
	}
	return service.CreateTurn(a.appContext(), request)
}

func (a *App) ListConversationTurns(conversationID string) ([]conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return nil, err
	}
	return service.ListTurns(a.appContext(), conversationID)
}

func (a *App) GetConversationTurn(turnID string) (conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Turn{}, err
	}
	return service.GetTurn(a.appContext(), turnID)
}

func (a *App) DeleteConversationTurn(conversationID, turnID string) (conversation.DeleteTurnResult, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.DeleteTurnResult{}, err
	}
	return service.DeleteTurn(a.appContext(), conversationID, turnID)
}

func (a *App) MoveConversationTurn(request conversation.MoveTurnRequest) (conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Turn{}, err
	}
	return service.MoveTurn(a.appContext(), request)
}

func (a *App) ReorderConversationTurns(request conversation.ReorderTurnsRequest) ([]conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return nil, err
	}
	return service.ReorderTurns(a.appContext(), request)
}

func (a *App) GetFinalConversationTurn(conversationID string) (*conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return nil, err
	}
	return service.GetFinalTurn(a.appContext(), conversationID)
}

func (a *App) MarkFinalConversationTurn(conversationID, turnID string) (conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Turn{}, err
	}
	return service.MarkFinalTurn(a.appContext(), conversationID, turnID)
}

func (a *App) RerunFinalConversationTurn(conversationID string) (RerunFinalResult, error) {
	conversations, err := a.conversationService()
	if err != nil {
		return RerunFinalResult{}, err
	}
	prepared, err := conversations.PrepareFinalRerun(a.appContext(), conversationID)
	if err != nil {
		return RerunFinalResult{}, err
	}
	analysis, err := a.analysisService()
	if err != nil {
		return RerunFinalResult{}, err
	}
	execution, err := analysis.Execute(a.appContext(), analysisruntime.ExecuteRequest{
		ConversationID: prepared.Conversation.ID,
		TurnID:         prepared.Turn.ID,
		Code:           prepared.Code,
		TimeoutSeconds: 360,
	}, func(event analysisruntime.WorkerEvent) {
		runtime.EventsEmit(a.appContext(), "agent-runtime-event", event)
	})
	if err != nil {
		return RerunFinalResult{}, err
	}
	turn, err := conversations.GetTurn(a.appContext(), prepared.Turn.ID)
	if err != nil {
		return RerunFinalResult{}, err
	}
	if turn.Status == conversation.TurnStatusCompleted {
		if _, err := conversations.MarkFinalTurn(a.appContext(), prepared.Conversation.ID, turn.ID); err != nil {
			return RerunFinalResult{}, err
		}
	}
	updatedConversation, err := conversations.GetConversation(a.appContext(), prepared.Conversation.ID)
	if err != nil {
		return RerunFinalResult{}, err
	}
	return RerunFinalResult{
		Conversation: updatedConversation,
		Turn:         turn,
		Answer:       prepared.SourceTurn.AssistantText,
		Code:         prepared.Code,
		Execution:    execution,
		Artifacts:    execution.Artifacts,
	}, nil
}

func (a *App) CompleteConversationTurn(request conversation.CompleteTurnRequest) (conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Turn{}, err
	}
	return service.CompleteTurn(a.appContext(), request)
}

func (a *App) FailConversationTurn(request conversation.FailTurnRequest) (conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.Turn{}, err
	}
	return service.FailTurn(a.appContext(), request)
}

func (a *App) ListTurnArtifacts(turnID string) ([]conversation.Artifact, error) {
	service, err := a.conversationService()
	if err != nil {
		return nil, err
	}
	return service.ListArtifacts(a.appContext(), turnID)
}

func (a *App) ListWorkspaceArtifacts(workspaceID, kind string) (artifactbrowser.ListResponse, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.ListResponse{}, err
	}
	return service.ListWorkspace(a.appContext(), workspaceID, kind)
}
func (a *App) ListTurnArtifactSummaries(conversationID, turnID, kind string) (artifactbrowser.ListResponse, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.ListResponse{}, err
	}
	return service.ListTurn(a.appContext(), conversationID, turnID, kind)
}
func (a *App) GetWorkspaceArtifactMetadata(workspaceID, artifactID string) (artifactbrowser.Metadata, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.Metadata{}, err
	}
	return service.MetadataForWorkspace(a.appContext(), workspaceID, artifactID)
}
func (a *App) GetTurnArtifactMetadata(conversationID, turnID, artifactID string) (artifactbrowser.Metadata, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.Metadata{}, err
	}
	return service.MetadataForTurn(a.appContext(), conversationID, turnID, artifactID)
}
func (a *App) GetWorkspaceArtifactRows(workspaceID, artifactID string, request artifactbrowser.RowsRequest) (artifactbrowser.RowsResult, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.RowsResult{}, err
	}
	return service.RowsForWorkspace(a.appContext(), workspaceID, artifactID, request)
}
func (a *App) GetTurnArtifactRows(conversationID, turnID, artifactID string, request artifactbrowser.RowsRequest) (artifactbrowser.RowsResult, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.RowsResult{}, err
	}
	return service.RowsForTurn(a.appContext(), conversationID, turnID, artifactID, request)
}
func (a *App) GetWorkspaceArtifactUsage(workspaceID string) (artifactbrowser.Usage, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.Usage{}, err
	}
	return service.Usage(a.appContext(), workspaceID)
}
func (a *App) DeleteWorkspaceArtifact(workspaceID, artifactID string) (artifactbrowser.DeleteResult, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.DeleteResult{}, err
	}
	return service.DeleteForWorkspace(a.appContext(), workspaceID, artifactID)
}
func (a *App) DeleteTurnArtifact(conversationID, turnID, artifactID string) (artifactbrowser.DeleteResult, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.DeleteResult{}, err
	}
	return service.DeleteForTurn(a.appContext(), conversationID, turnID, artifactID)
}

func (a *App) DeleteConversation(conversationID string) (conversation.DeleteResult, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.DeleteResult{}, err
	}
	return service.DeleteConversation(a.appContext(), conversationID)
}

func (a *App) ExecuteConversationCode(request analysisruntime.ExecuteRequest) (analysisruntime.ExecuteResult, error) {
	service, err := a.analysisService()
	if err != nil {
		return analysisruntime.ExecuteResult{}, err
	}
	return service.Execute(a.appContext(), request, func(event analysisruntime.WorkerEvent) {
		runtime.EventsEmit(a.appContext(), "analysis-runtime-event", event)
	})
}

func (a *App) RunManualCode(request manualanalysis.RunRequest) (manualanalysis.RunResult, error) {
	service, err := a.manualAnalysisService()
	if err != nil {
		return manualanalysis.RunResult{}, err
	}
	return service.Run(a.appContext(), request, func(event analysisruntime.WorkerEvent) {
		runtime.EventsEmit(a.appContext(), "analysis-runtime-event", event)
	})
}

func (a *App) AnalyzeQuestion(request analysisagent.AnalyzeRequest) (analysisagent.AnalyzeResult, error) {
	service, err := a.agentService()
	if err != nil {
		return analysisagent.AnalyzeResult{}, err
	}
	return service.Analyze(a.appContext(), request, func(event analysisruntime.WorkerEvent) {
		runtime.EventsEmit(a.appContext(), "agent-runtime-event", event)
	})
}

func (a *App) GetWorkspaceKernelStatus(workspaceID string) (analysisruntime.KernelStatus, error) {
	service, err := a.analysisService()
	if err != nil {
		return analysisruntime.KernelStatus{}, err
	}
	return service.Status(a.appContext(), workspaceID)
}

func (a *App) ResetWorkspaceKernel(workspaceID string) (bool, error) {
	service, err := a.analysisService()
	if err != nil {
		return false, err
	}
	return service.Reset(a.appContext(), workspaceID)
}

func (a *App) InterruptWorkspaceKernel(workspaceID string) (bool, error) {
	service, err := a.analysisService()
	if err != nil {
		return false, err
	}
	agentCancelled := false
	if a.agent != nil {
		agentCancelled, _ = a.agent.Cancel(a.appContext(), workspaceID)
	}
	kernelInterrupted, err := service.Interrupt(a.appContext(), workspaceID)
	return agentCancelled || kernelInterrupted, err
}

func (a *App) PrepareWorkspaceCatalog(workspaceID string) (datacatalog.Catalog, error) {
	service, err := a.catalogService()
	if err != nil {
		return datacatalog.Catalog{}, err
	}
	return service.Prepare(a.appContext(), workspaceID)
}

func (a *App) ListWorkspaceDatasets(workspaceID string) (datacatalog.DatasetListResponse, error) {
	service, err := a.catalogService()
	if err != nil {
		return datacatalog.DatasetListResponse{}, err
	}
	return service.ListDatasets(a.appContext(), workspaceID)
}

func (a *App) SelectWorkspaceDataset(workspaceID, sourcePath, tableName string) (datacatalog.Dataset, error) {
	service, err := a.catalogService()
	if err != nil {
		return datacatalog.Dataset{}, err
	}
	return service.FindDataset(a.appContext(), workspaceID, sourcePath, tableName)
}

func (a *App) GetWorkspaceDatasetSchema(workspaceID, tableName string) (datacatalog.DatasetSchema, error) {
	service, err := a.catalogService()
	if err != nil {
		return datacatalog.DatasetSchema{}, err
	}
	return service.GetSchema(a.appContext(), workspaceID, tableName)
}

func (a *App) SaveWorkspaceDatasetSchema(request datacatalog.SaveSchemaRequest) (datacatalog.DatasetSchema, error) {
	catalogService, err := a.catalogService()
	if err != nil {
		return datacatalog.DatasetSchema{}, err
	}
	saved, err := catalogService.SaveSchema(a.appContext(), request)
	if err != nil {
		return datacatalog.DatasetSchema{}, err
	}
	if request.Context == nil {
		return saved, nil
	}
	workspaceService, err := a.workspaceService()
	if err != nil {
		return datacatalog.DatasetSchema{}, err
	}
	summary, err := workspaceService.Summary(a.appContext(), request.WorkspaceID)
	if err != nil {
		return datacatalog.DatasetSchema{}, err
	}
	if _, err := workspaceService.Update(a.appContext(), workspace.UpdateRequest{
		WorkspaceID: request.WorkspaceID, Name: summary.Name, SchemaContext: request.Context,
	}); err != nil {
		return datacatalog.DatasetSchema{}, err
	}
	return catalogService.GetSchema(a.appContext(), request.WorkspaceID, request.TableName)
}

func (a *App) RegenerateWorkspaceDatasetSchema(request schemageneration.RegenerateRequest) (schemageneration.RegenerateResult, error) {
	service, err := a.schemaGenerationService()
	if err != nil {
		return schemageneration.RegenerateResult{}, err
	}
	return service.Regenerate(a.appContext(), request)
}

func (a *App) ListWorkspaceColumns(workspaceID string) (datacatalog.WorkspaceColumnsResponse, error) {
	service, err := a.catalogService()
	if err != nil {
		return datacatalog.WorkspaceColumnsResponse{}, err
	}
	return service.ListColumns(a.appContext(), workspaceID)
}

type WorkspacePaths struct {
	WorkspaceDirectory string `json:"workspace_dir"`
	DuckDBPath         string `json:"duckdb_path"`
	TerminalEnabled    bool   `json:"terminal_enabled"`
}

func (a *App) GetWorkspacePaths(workspaceID string) (WorkspacePaths, error) {
	service, err := a.workspaceService()
	if err != nil {
		return WorkspacePaths{}, err
	}
	summary, err := service.Summary(a.appContext(), workspaceID)
	if err != nil {
		return WorkspacePaths{}, err
	}
	directory := filepath.Join(a.paths.DataDir, "workspaces", summary.ID)
	return WorkspacePaths{
		WorkspaceDirectory: directory,
		DuckDBPath:         filepath.Join(directory, "workspace.duckdb"),
		TerminalEnabled:    false,
	}, nil
}

func (a *App) ListConnections(workspaceID string) (connection.ListResponse, error) {
	service, err := a.connectionService()
	if err != nil {
		return connection.ListResponse{}, err
	}
	return service.List(a.appContext(), workspaceID)
}

func (a *App) DiscoverLocalConnection(request connection.DiscoverRequest) (connection.Discovery, error) {
	service, err := a.connectionService()
	if err != nil {
		return connection.Discovery{}, err
	}
	return service.Discover(a.appContext(), request)
}

func (a *App) PreviewLocalConnection(request connection.PreviewRequest) (connection.Preview, error) {
	service, err := a.connectionService()
	if err != nil {
		return connection.Preview{}, err
	}
	return service.Preview(a.appContext(), request)
}

func (a *App) CreateLocalConnection(request connection.CreateRequest) (connection.Connection, error) {
	service, err := a.connectionService()
	if err != nil {
		return connection.Connection{}, err
	}
	return service.Create(a.appContext(), request)
}

func (a *App) RefreshConnection(connectionID string) (connection.Connection, error) {
	service, err := a.connectionService()
	if err != nil {
		return connection.Connection{}, err
	}
	return service.Refresh(a.appContext(), connectionID)
}

func (a *App) DeleteConnection(connectionID string) (connection.DeleteResult, error) {
	service, err := a.connectionService()
	if err != nil {
		return connection.DeleteResult{}, err
	}
	if err := service.Delete(a.appContext(), connectionID); err != nil {
		return connection.DeleteResult{}, err
	}
	return connection.DeleteResult{Deleted: true}, nil
}

type LocalConnectionFileSelection struct {
	SourcePath  string                 `json:"source_path"`
	AdapterKind connection.AdapterKind `json:"adapter_kind"`
}

func (a *App) ChooseLocalConnectionFile() (LocalConnectionFileSelection, error) {
	path, err := runtime.OpenFileDialog(a.appContext(), runtime.OpenDialogOptions{
		Title: "Choose a local data source",
		Filters: []runtime.FileFilter{
			{DisplayName: "CSV, Parquet, or Excel", Pattern: "*.csv;*.CSV;*.parquet;*.PARQUET;*.xlsx;*.XLSX"},
			{DisplayName: "CSV", Pattern: "*.csv;*.CSV"},
			{DisplayName: "Parquet", Pattern: "*.parquet;*.PARQUET"},
			{DisplayName: "Excel workbook", Pattern: "*.xlsx;*.XLSX"},
		},
	})
	if err != nil || path == "" {
		return LocalConnectionFileSelection{}, err
	}
	kind, err := connection.AdapterKindForPath(path)
	if err != nil {
		return LocalConnectionFileSelection{}, err
	}
	return LocalConnectionFileSelection{SourcePath: path, AdapterKind: kind}, nil
}

// RuntimeStatus reports the embedded UV bundle and supported provisioning modes.
func (a *App) RuntimeStatus() runtimeprovision.Status {
	return a.provisioner.Status()
}

// RuntimeDiagnostics extracts and executes bundled UV to verify the payload.
func (a *App) RuntimeDiagnostics() runtimeprovision.Diagnostics {
	return a.provisioner.Diagnostics(a.appContext())
}

// RuntimePlan validates a runtime configuration without changing the machine.
func (a *App) RuntimePlan(config runtimeprovision.Config) (runtimeprovision.Plan, error) {
	return a.provisioner.Plan(config)
}

// ProvisionRuntime creates the selected Python runtime using the embedded UV binary.
func (a *App) ProvisionRuntime(config runtimeprovision.Config) (runtimeprovision.Result, error) {
	return a.provisioner.Provision(a.appContext(), config)
}
