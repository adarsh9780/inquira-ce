package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/wailsapp/wails/v2/pkg/runtime"

	"github.com/adarsh9780/inquira-ce/internal/analysisagent"
	"github.com/adarsh9780/inquira-ce/internal/analysisruntime"
	"github.com/adarsh9780/inquira-ce/internal/appdirs"
	"github.com/adarsh9780/inquira-ce/internal/apperror"
	"github.com/adarsh9780/inquira-ce/internal/artifactbrowser"
	"github.com/adarsh9780/inquira-ce/internal/connection"
	"github.com/adarsh9780/inquira-ce/internal/conversation"
	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
	"github.com/adarsh9780/inquira-ce/internal/desktop"
	"github.com/adarsh9780/inquira-ce/internal/legal"
	"github.com/adarsh9780/inquira-ce/internal/localstate"
	"github.com/adarsh9780/inquira-ce/internal/manualanalysis"
	"github.com/adarsh9780/inquira-ce/internal/modelconfig"
	"github.com/adarsh9780/inquira-ce/internal/netclient"
	"github.com/adarsh9780/inquira-ce/internal/runtimeprovision"
	"github.com/adarsh9780/inquira-ce/internal/schemageneration"
	"github.com/adarsh9780/inquira-ce/internal/slashcommand"
	terminalruntime "github.com/adarsh9780/inquira-ce/internal/terminal"
	workerruntime "github.com/adarsh9780/inquira-ce/internal/worker"
	"github.com/adarsh9780/inquira-ce/internal/workspace"
	dataworkerbundle "github.com/adarsh9780/inquira-ce/python/data_worker"
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
	commands      *slashcommand.Service
	schemas       *schemageneration.Service
	agent         *analysisagent.Service
	worker        *workerruntime.PersistentTransport
	catalog       *datacatalog.Service
	terminals     *terminalruntime.Service
	desktop       *desktop.Service
	localState    localstate.Repository
	saveDialog    func(context.Context, runtime.SaveDialogOptions) (string, error)
	startupLog    sync.Once
	initErr       error
}

// NewApp creates a new App application struct
func NewApp() *App {
	app := &App{desktop: desktop.New(), saveDialog: runtime.SaveFileDialog}
	paths, err := appdirs.Resolve()
	if err != nil {
		if logsDir, fallbackErr := createFallbackStartupLogDirectory(os.TempDir()); fallbackErr == nil {
			app.paths.LogsDir = logsDir
		}
		app.initErr = err
		return app
	}
	app.paths = paths
	app.terminals = terminalruntime.NewPlatformService(func(eventName string, payload any) {
		if app.ctx != nil {
			runtime.EventsEmit(app.ctx, eventName, payload)
		}
	})
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
	app.workspaces = workspace.NewService(workspaceRepository).WithModelSource(app.models)
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
		app.catalog, app.workspaces, schemageneration.NewWorkerGateway(transport),
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
	app.commands = slashcommand.NewService(
		app.conversations, app.catalog, slashcommand.NewWorkerGateway(transport), app.analysis,
	)
	app.agent = analysisagent.NewService(
		app.conversations, app.catalog, app.workspaces, analysisagent.NewWorkerGateway(transport), app.analysis,
	)
	localStateRepository, err := localstate.OpenSQLite(paths.DatabasePath)
	if err != nil {
		_ = app.worker.Close()
		_ = app.conversations.Close()
		_ = app.catalog.Close()
		_ = app.connections.Close()
		_ = app.workspaces.Close()
		_ = app.models.Close()
		app.initErr = err
		return app
	}
	app.localState = localStateRepository
	return app
}

func createFallbackStartupLogDirectory(root string) (string, error) {
	return os.MkdirTemp(root, "inquira-startup-logs-")
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) shutdown(context.Context) {
	if a.terminals != nil {
		_ = a.terminals.Close()
	}
	if a.worker != nil {
		_ = a.worker.Close()
	}
	if a.conversations != nil {
		_ = a.conversations.Close()
	}
	if a.localState != nil {
		_ = a.localState.Close()
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

func (a *App) slashCommandService() (*slashcommand.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.commands == nil {
		return nil, apperror.New("slash_commands_unavailable", "Workspace commands are unavailable.")
	}
	return a.commands, nil
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

func (a *App) terminalService() (*terminalruntime.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.terminals == nil {
		return nil, apperror.New("terminal_unavailable", "The local terminal is unavailable.")
	}
	return a.terminals, nil
}

func (a *App) localStateRepository() (localstate.Repository, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	if a.localState == nil {
		return nil, apperror.New("local_state_unavailable", "Local session storage is unavailable.")
	}
	return a.localState, nil
}

type StartupSnapshot struct {
	Ready   bool   `json:"ready"`
	Error   string `json:"error"`
	Message string `json:"message"`
}

func (a *App) GetStartupState() StartupSnapshot {
	state := StartupSnapshot{Ready: a.initErr == nil}
	if a.initErr != nil {
		state.Error = "Inquira could not initialize its local services: " + a.initErr.Error()
	}
	a.startupLog.Do(func() {
		message := "Desktop startup ready."
		if state.Error != "" {
			message = state.Error
		}
		if a.paths.LogsDir != "" {
			_, _ = desktop.AppendStartupLog(a.paths.LogsDir, message)
		}
	})
	return state
}

func (a *App) OpenExternalURL(rawURL string) error {
	if a.desktop == nil {
		return apperror.New("desktop_unavailable", "Desktop integration is unavailable.")
	}
	return a.desktop.OpenExternalURL(rawURL)
}

func (a *App) GetTermsAndConditions() legal.Terms {
	return legal.CurrentTerms()
}

func (a *App) SaveExportFile(request desktop.ExportRequest) (bool, error) {
	prepared, err := desktop.PrepareExport(request)
	if err != nil {
		return false, err
	}
	if a.saveDialog == nil {
		return false, apperror.New("desktop_unavailable", "The desktop save dialog is unavailable.")
	}
	filters := make([]runtime.FileFilter, 0, len(prepared.Filters))
	for _, filter := range prepared.Filters {
		patterns := make([]string, 0, len(filter.Extensions))
		for _, extension := range filter.Extensions {
			patterns = append(patterns, "*."+extension)
		}
		filters = append(filters, runtime.FileFilter{DisplayName: filter.Name, Pattern: strings.Join(patterns, ";")})
	}
	target, err := a.saveDialog(a.appContext(), runtime.SaveDialogOptions{
		Title:                "Export file",
		DefaultFilename:      prepared.DefaultFileName,
		Filters:              filters,
		CanCreateDirectories: true,
	})
	if err != nil {
		return false, fmt.Errorf("open export save dialog: %w", err)
	}
	if target == "" {
		return false, nil
	}
	if err := desktop.WriteExport(target, prepared.Content); err != nil {
		return false, err
	}
	return true, nil
}

func (a *App) LoadLocalState(scope string) (localstate.Snapshot, error) {
	repository, err := a.localStateRepository()
	if err != nil {
		return nil, err
	}
	snapshot, found, err := repository.Load(a.appContext(), scope)
	if err != nil {
		return nil, err
	}
	if !found {
		return nil, nil
	}
	return snapshot, nil
}

func (a *App) SaveLocalState(scope string, snapshot localstate.Snapshot) (bool, error) {
	repository, err := a.localStateRepository()
	if err != nil {
		return false, err
	}
	if err := repository.Save(a.appContext(), scope, snapshot); err != nil {
		return false, err
	}
	return true, nil
}

func (a *App) OpenStartupLogs() error {
	if a.desktop == nil || a.paths.LogsDir == "" {
		return apperror.New("desktop_unavailable", "Startup diagnostics are unavailable.")
	}
	if _, err := desktop.AppendStartupLog(a.paths.LogsDir, "Startup diagnostics opened by the user."); err != nil {
		return err
	}
	return a.desktop.OpenDirectory(a.paths.LogsDir)
}

func (a *App) RestartDesktopApp() error {
	if a.desktop == nil {
		return apperror.New("desktop_unavailable", "Desktop restart is unavailable.")
	}
	if err := a.desktop.Restart(); err != nil {
		return err
	}
	if a.ctx != nil {
		runtime.Quit(a.ctx)
	}
	return nil
}

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

func (a *App) GetWorkspaceAIConfig(workspaceID string) (workspace.AIConfigResponse, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.AIConfigResponse{}, err
	}
	return service.GetAIConfig(a.appContext(), workspaceID)
}

func (a *App) UpdateWorkspaceAIConfig(workspaceID string, request workspace.AIConfigUpdateRequest) (workspace.AIConfigResponse, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.AIConfigResponse{}, err
	}
	return service.UpdateAIConfig(a.appContext(), workspaceID, request)
}

func (a *App) DeleteWorkspace(workspaceID string) (workspace.DeletionResult, error) {
	service, err := a.workspaceService()
	if err != nil {
		return workspace.DeletionResult{}, err
	}
	if a.terminals != nil {
		_, _ = a.terminals.Stop("workspace:" + strings.TrimSpace(workspaceID))
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

func (a *App) ListConversationTurns(conversationID string) ([]conversation.Turn, error) {
	service, err := a.conversationService()
	if err != nil {
		return nil, err
	}
	return service.ListTurns(a.appContext(), conversationID)
}

func (a *App) ListConversationTurnPage(conversationID string, limit int, before string) (conversation.TurnPage, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.TurnPage{}, err
	}
	return service.ListTurnPage(a.appContext(), conversationID, limit, before)
}

func (a *App) GetConversationUsage(conversationID string) (conversation.ConversationUsage, error) {
	service, err := a.conversationService()
	if err != nil {
		return conversation.ConversationUsage{}, err
	}
	return service.GetConversationUsage(a.appContext(), conversationID)
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

func (a *App) ListTurnArtifactSummaries(conversationID, turnID, kind string) (artifactbrowser.ListResponse, error) {
	service, err := a.artifactService()
	if err != nil {
		return artifactbrowser.ListResponse{}, err
	}
	return service.ListTurn(a.appContext(), conversationID, turnID, kind)
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

func (a *App) RunManualCode(request manualanalysis.RunRequest) (manualanalysis.RunResult, error) {
	service, err := a.manualAnalysisService()
	if err != nil {
		return manualanalysis.RunResult{}, err
	}
	return service.Run(a.appContext(), request, func(event analysisruntime.WorkerEvent) {
		runtime.EventsEmit(a.appContext(), "analysis-runtime-event", event)
	})
}

func (a *App) ExecuteWorkspaceCommand(request slashcommand.ExecuteRequest) (slashcommand.ExecuteResult, error) {
	service, err := a.slashCommandService()
	if err != nil {
		return slashcommand.ExecuteResult{}, err
	}
	return service.Execute(a.appContext(), request, func(event analysisruntime.WorkerEvent) {
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

func (a *App) CancelAgentAnalysis(workspaceID, clientRequestID string) (bool, error) {
	service, err := a.agentService()
	if err != nil {
		return false, err
	}
	return service.Cancel(a.appContext(), workspaceID, clientRequestID)
}

func (a *App) GetWorkspaceKernelStatus(workspaceID string) (analysisruntime.KernelStatus, error) {
	service, err := a.analysisService()
	if err != nil {
		return analysisruntime.KernelStatus{}, err
	}
	return service.Status(a.appContext(), workspaceID)
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

func (a *App) StartTerminalSession(request terminalruntime.StartRequest) (terminalruntime.StartResponse, error) {
	service, err := a.terminalService()
	if err != nil {
		return terminalruntime.StartResponse{}, err
	}
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	workspaceService, err := a.workspaceService()
	if err != nil {
		return terminalruntime.StartResponse{}, err
	}
	summary, err := workspaceService.Summary(a.appContext(), workspaceID)
	if err != nil {
		return terminalruntime.StartResponse{}, err
	}
	expectedSessionID := "workspace:" + summary.ID
	if strings.TrimSpace(request.SessionID) != expectedSessionID {
		return terminalruntime.StartResponse{}, apperror.New("terminal_session_invalid", "The terminal session does not match the active workspace.")
	}
	directory := filepath.Join(a.paths.DataDir, "workspaces", summary.ID)
	if err := os.MkdirAll(directory, 0o700); err != nil {
		return terminalruntime.StartResponse{}, fmt.Errorf("prepare terminal workspace: %w", err)
	}
	request.Cwd = directory
	return service.Start(a.appContext(), request)
}

func (a *App) WriteTerminalSession(sessionID, data string) error {
	service, err := a.terminalService()
	if err != nil {
		return err
	}
	return service.Write(sessionID, data)
}

func (a *App) ResizeTerminalSession(sessionID string, cols, rows int) error {
	service, err := a.terminalService()
	if err != nil {
		return err
	}
	return service.Resize(sessionID, cols, rows)
}

func (a *App) StopTerminalSession(sessionID string) (terminalruntime.StopResponse, error) {
	service, err := a.terminalService()
	if err != nil {
		return terminalruntime.StopResponse{}, err
	}
	stopped, err := service.Stop(sessionID)
	return terminalruntime.StopResponse{SessionID: strings.TrimSpace(sessionID), Stopped: stopped}, err
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
			{DisplayName: "Supported data sources", Pattern: "*.csv;*.CSV;*.parquet;*.PARQUET;*.xlsx;*.XLSX;*.json;*.JSON;*.jsonl;*.JSONL;*.ndjson;*.NDJSON;*.sqlite;*.SQLITE;*.sqlite3;*.SQLITE3;*.db;*.DB"},
			{DisplayName: "CSV", Pattern: "*.csv;*.CSV"},
			{DisplayName: "Parquet", Pattern: "*.parquet;*.PARQUET"},
			{DisplayName: "Excel workbook", Pattern: "*.xlsx;*.XLSX"},
			{DisplayName: "JSON", Pattern: "*.json;*.JSON;*.jsonl;*.JSONL;*.ndjson;*.NDJSON"},
			{DisplayName: "SQLite database", Pattern: "*.sqlite;*.SQLITE;*.sqlite3;*.SQLITE3;*.db;*.DB"},
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

func (a *App) ChoosePythonExecutable() (string, error) {
	return runtime.OpenFileDialog(a.appContext(), runtime.OpenDialogOptions{
		Title: "Choose an organization-provided Python 3.12 executable",
		Filters: []runtime.FileFilter{
			{DisplayName: "Python executable", Pattern: "python;python3;python3.12;python.exe;*.exe"},
			{DisplayName: "All files", Pattern: "*"},
		},
	})
}

func (a *App) ChooseCertificateBundle() (string, error) {
	return runtime.OpenFileDialog(a.appContext(), runtime.OpenDialogOptions{
		Title: "Choose a PEM certificate bundle",
		Filters: []runtime.FileFilter{
			{DisplayName: "Certificate bundle", Pattern: "*.pem;*.crt;*.cer"},
			{DisplayName: "All files", Pattern: "*"},
		},
	})
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
	return a.provisioner.PlanPreview(config)
}

func (a *App) emitRuntimeProgress(progress runtimeprovision.Progress) {
	if a.ctx != nil {
		runtime.EventsEmit(a.ctx, runtimeprovision.RuntimeProgressEvent, progress)
	}
}

// ProvisionRuntime creates the selected Python runtime using the embedded UV binary.
func (a *App) ProvisionRuntime(config runtimeprovision.Config) (runtimeprovision.Result, error) {
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return runtimeprovision.Result{}, fmt.Errorf("stop the active data worker before runtime setup: %w", err)
		}
	}
	result, err := a.provisioner.ProvisionWithProgress(a.appContext(), config, a.emitRuntimeProgress)
	if err != nil {
		return runtimeprovision.Result{}, err
	}
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return runtimeprovision.Result{}, fmt.Errorf("restart the data worker after runtime setup: %w", err)
		}
	}
	return result, nil
}

// CancelRuntimeProvisioning cancels the active setup command without changing
// the previously verified runtime.
func (a *App) CancelRuntimeProvisioning() bool {
	return a.provisioner.Cancel()
}

// RepairRuntime transactionally rebuilds the runtime from its saved,
// non-secret configuration. The existing verified environment remains active
// if repair is cancelled or fails.
func (a *App) RepairRuntime() (runtimeprovision.Result, error) {
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return runtimeprovision.Result{}, fmt.Errorf("stop the active data worker before runtime repair: %w", err)
		}
	}
	result, err := a.provisioner.Repair(a.appContext(), a.emitRuntimeProgress)
	if err != nil {
		return runtimeprovision.Result{}, err
	}
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return runtimeprovision.Result{}, fmt.Errorf("restart the data worker after runtime repair: %w", err)
		}
	}
	return result, nil
}

// ResetRuntime removes only Inquira-managed runtime installations. Workspace
// data and connected source files are not part of the runtime directory.
func (a *App) ResetRuntime() (bool, error) {
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return false, fmt.Errorf("stop the active data worker before runtime reset: %w", err)
		}
	}
	if err := a.provisioner.Reset(a.emitRuntimeProgress); err != nil {
		return false, err
	}
	return true, nil
}

// ExportRuntimeDiagnostics writes a bounded JSON report containing runtime
// versions and health flags. The report excludes paths, workspace data,
// credentials, network configuration, and raw command output.
func (a *App) ExportRuntimeDiagnostics() (bool, error) {
	report := a.provisioner.DiagnosticReport(a.appContext())
	content, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return false, fmt.Errorf("encode runtime diagnostics: %w", err)
	}
	return a.SaveExportFile(desktop.ExportRequest{
		DefaultFileName: "inquira-runtime-diagnostics.json",
		ContentBase64:   base64.StdEncoding.EncodeToString(append(content, '\n')),
		Filters: []desktop.ExportFilter{
			{Name: "JSON diagnostics", Extensions: []string{"json"}},
		},
	})
}

// RollbackRuntime restores the last verified runtime and keeps the replaced
// environment available in case the user needs to reverse the rollback.
func (a *App) RollbackRuntime() (runtimeprovision.Result, error) {
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return runtimeprovision.Result{}, fmt.Errorf("stop the active data worker before runtime rollback: %w", err)
		}
	}
	result, err := a.provisioner.RollbackWithProgress(a.emitRuntimeProgress)
	if err != nil {
		return runtimeprovision.Result{}, err
	}
	if a.worker != nil {
		if err := a.worker.Stop(); err != nil {
			return runtimeprovision.Result{}, fmt.Errorf("restart the data worker after runtime rollback: %w", err)
		}
	}
	return result, nil
}
