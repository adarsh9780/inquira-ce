package runtimeprovision

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
)

type Step struct {
	Name       string   `json:"name"`
	Executable string   `json:"executable"`
	Arguments  []string `json:"arguments"`
}

type Plan struct {
	Mode        Mode              `json:"mode"`
	Environment map[string]string `json:"environment"`
	Steps       []Step            `json:"steps"`
}

type Status struct {
	RuntimeRoot     string     `json:"runtimeRoot"`
	BundleAvailable bool       `json:"bundleAvailable"`
	Bundle          BundleInfo `json:"bundle"`
	BundleError     string     `json:"bundleError,omitempty"`
	SupportedModes  []Mode     `json:"supportedModes"`
}

type Diagnostics struct {
	Status    Status `json:"status"`
	UVVersion string `json:"uvVersion,omitempty"`
	Error     string `json:"error,omitempty"`
}

type Result struct {
	Mode             Mode   `json:"mode"`
	PythonExecutable string `json:"pythonExecutable"`
	UVExecutable     string `json:"uvExecutable"`
}

type commandRunner func(context.Context, map[string]string, Step) error

type Provisioner struct {
	runtimeRoot string
	runner      commandRunner
}

func NewProvisioner(runtimeRoot string) *Provisioner {
	return &Provisioner{runtimeRoot: runtimeRoot, runner: runStep}
}

func (p *Provisioner) Status() Status {
	info, err := loadBundleInfo(bundledAssets)
	status := Status{
		RuntimeRoot:    p.runtimeRoot,
		Bundle:         info,
		SupportedModes: SupportedModes(),
	}
	if err != nil {
		status.BundleError = err.Error()
		return status
	}
	status.BundleAvailable = true
	return status
}

// Diagnostics extracts and executes the embedded UV binary. It is used by the
// packaged executable's runtime-info command to verify the complete bundle.
func (p *Provisioner) Diagnostics(ctx context.Context) Diagnostics {
	diagnostics := Diagnostics{Status: p.Status()}
	uvPath, _, err := extractBundle(bundledAssets, filepath.Join(p.runtimeRoot, "tools"))
	if err != nil {
		diagnostics.Error = err.Error()
		return diagnostics
	}
	command := exec.CommandContext(ctx, uvPath, "--version")
	output, err := command.CombinedOutput()
	if err != nil {
		diagnostics.Error = strings.TrimSpace(string(output))
		if diagnostics.Error == "" {
			diagnostics.Error = err.Error()
		}
		return diagnostics
	}
	diagnostics.UVVersion = strings.TrimSpace(string(output))
	return diagnostics
}

func (p *Provisioner) Plan(config Config) (Plan, error) {
	if err := config.Validate(); err != nil {
		return Plan{}, err
	}

	uvPath := filepath.Join(p.runtimeRoot, "tools", executableName("uv"))
	pythonDir := filepath.Join(p.runtimeRoot, "python")
	environmentDir := filepath.Join(p.runtimeRoot, "environments", "data-worker")
	environment := map[string]string{
		"UV_PYTHON_INSTALL_DIR":  pythonDir,
		"UV_PROJECT_ENVIRONMENT": environmentDir,
	}
	if config.UseSystemCerts {
		environment["UV_SYSTEM_CERTS"] = "true"
	}

	plan := Plan{Mode: config.Mode, Environment: environment}
	switch config.Mode {
	case ModeManaged:
		plan.Steps = []Step{
			{Name: "install-python", Executable: uvPath, Arguments: []string{"python", "install", config.PythonVersion, "--install-dir", pythonDir, "--no-progress"}},
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonVersion, "--managed-python"}},
		}
	case ModeExternalPython:
		environment["UV_NO_MANAGED_PYTHON"] = "true"
		plan.Steps = []Step{
			{Name: "validate-external-python", Executable: config.PythonExecutable, Arguments: []string{"--version"}},
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonExecutable, "--no-python-downloads"}},
		}
	case ModeInternalMirror:
		environment["UV_PYTHON_INSTALL_MIRROR"] = config.PythonInstallMirror
		environment["UV_DEFAULT_INDEX"] = config.DefaultIndex
		plan.Steps = []Step{
			{Name: "install-python-from-mirror", Executable: uvPath, Arguments: []string{"python", "install", config.PythonVersion, "--install-dir", pythonDir, "--no-progress"}},
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonVersion, "--managed-python"}},
		}
	}
	return plan, nil
}

func (p *Provisioner) Provision(ctx context.Context, config Config) (Result, error) {
	uvPath, _, err := extractBundle(bundledAssets, filepath.Join(p.runtimeRoot, "tools"))
	if err != nil {
		return Result{}, err
	}
	plan, err := p.Plan(config)
	if err != nil {
		return Result{}, err
	}
	for index := range plan.Steps {
		if strings.HasSuffix(plan.Steps[index].Executable, executableName("uv")) {
			plan.Steps[index].Executable = uvPath
		}
		if err := p.runner(ctx, plan.Environment, plan.Steps[index]); err != nil {
			return Result{}, fmt.Errorf("%s: %w", plan.Steps[index].Name, err)
		}
	}

	return Result{
		Mode:             config.Mode,
		PythonExecutable: environmentPython(filepath.Join(p.runtimeRoot, "environments", "data-worker")),
		UVExecutable:     uvPath,
	}, nil
}

func runStep(ctx context.Context, environment map[string]string, step Step) error {
	command := exec.CommandContext(ctx, step.Executable, step.Arguments...)
	command.Env = append(os.Environ(), sortedEnvironment(environment)...)
	output, err := command.CombinedOutput()
	if err != nil {
		message := strings.TrimSpace(string(output))
		if message == "" {
			message = err.Error()
		}
		return fmt.Errorf("%s", message)
	}
	return nil
}

func sortedEnvironment(values map[string]string) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := make([]string, 0, len(keys))
	for _, key := range keys {
		result = append(result, key+"="+values[key])
	}
	return result
}

func executableName(base string) string {
	if runtime.GOOS == "windows" {
		return base + ".exe"
	}
	return base
}

func environmentPython(environmentDir string) string {
	if runtime.GOOS == "windows" {
		return filepath.Join(environmentDir, "Scripts", "python.exe")
	}
	return filepath.Join(environmentDir, "bin", "python")
}
