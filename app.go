package main

import (
	"context"
	"os"
	"path/filepath"

	"inquira-go/internal/runtimeprovision"
)

// App struct
type App struct {
	ctx         context.Context
	provisioner *runtimeprovision.Provisioner
}

// NewApp creates a new App application struct
func NewApp() *App {
	configDir, err := os.UserConfigDir()
	if err != nil || configDir == "" {
		configDir = os.TempDir()
	}
	return &App{
		provisioner: runtimeprovision.NewProvisioner(
			filepath.Join(configDir, "Inquira", "runtime"),
		),
	}
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

// RuntimeStatus reports the embedded UV bundle and supported provisioning modes.
func (a *App) RuntimeStatus() runtimeprovision.Status {
	return a.provisioner.Status()
}

// RuntimeDiagnostics extracts and executes bundled UV to verify the payload.
func (a *App) RuntimeDiagnostics() runtimeprovision.Diagnostics {
	ctx := a.ctx
	if ctx == nil {
		ctx = context.Background()
	}
	return a.provisioner.Diagnostics(ctx)
}

// RuntimePlan validates a runtime configuration without changing the machine.
func (a *App) RuntimePlan(config runtimeprovision.Config) (runtimeprovision.Plan, error) {
	return a.provisioner.Plan(config)
}

// ProvisionRuntime creates the selected Python runtime using the embedded UV binary.
func (a *App) ProvisionRuntime(config runtimeprovision.Config) (runtimeprovision.Result, error) {
	return a.provisioner.Provision(a.ctx, config)
}
