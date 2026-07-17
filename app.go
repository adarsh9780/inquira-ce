package main

import (
	"context"

	"inquira-go/internal/appdirs"
	"inquira-go/internal/modelconfig"
	"inquira-go/internal/netclient"
	"inquira-go/internal/runtimeprovision"
	"inquira-go/internal/workspace"
)

// App struct
type App struct {
	ctx         context.Context
	paths       appdirs.Paths
	provisioner *runtimeprovision.Provisioner
	models      *modelconfig.Service
	workspaces  *workspace.Service
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
	return app
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) shutdown(context.Context) {
	if a.workspaces != nil {
		_ = a.workspaces.Close()
	}
	if a.models != nil {
		_ = a.models.Close()
	}
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
	return service.Delete(a.appContext(), workspaceID)
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
