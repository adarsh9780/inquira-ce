package main

import (
	"context"
	"path/filepath"

	"github.com/wailsapp/wails/v2/pkg/runtime"

	"inquira-go/internal/appdirs"
	"inquira-go/internal/connection"
	"inquira-go/internal/modelconfig"
	"inquira-go/internal/netclient"
	"inquira-go/internal/runtimeprovision"
	"inquira-go/internal/workspace"
	dataworkerbundle "inquira-go/python/data_worker"
)

// App struct
type App struct {
	ctx         context.Context
	paths       appdirs.Paths
	provisioner *runtimeprovision.Provisioner
	models      *modelconfig.Service
	workspaces  *workspace.Service
	connections *connection.Service
	initErr     error
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
	transport := connection.NewSubprocessTransport(
		app.provisioner.PythonExecutable(), filepath.Join(workerProject, "src"), nil,
	).WithReadinessCheck(app.provisioner.Ready)
	app.connections = connection.NewService(
		connectionRepository, connection.NewWorkerGateway(transport), filepath.Join(paths.DataDir, "snapshots"),
	)
	return app
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) shutdown(context.Context) {
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

func (a *App) connectionService() (*connection.Service, error) {
	if a.initErr != nil {
		return nil, a.initErr
	}
	return a.connections, nil
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
	service, err := a.workspaceService()
	if err != nil {
		return workspace.Summary{}, err
	}
	return service.Summary(a.appContext(), workspaceID)
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
	if err := connectionService.DeleteWorkspaceConnections(a.appContext(), workspaceID); err != nil {
		return workspace.DeletionResult{}, err
	}
	return service.Delete(a.appContext(), workspaceID)
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
