package runtimeprovision

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
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
	RuntimeRoot      string     `json:"runtimeRoot"`
	BundleAvailable  bool       `json:"bundleAvailable"`
	Bundle           BundleInfo `json:"bundle"`
	BundleError      string     `json:"bundleError,omitempty"`
	SupportedModes   []Mode     `json:"supportedModes"`
	Ready            bool       `json:"ready"`
	PythonExecutable string     `json:"pythonExecutable"`
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
		RuntimeRoot:      p.runtimeRoot,
		Bundle:           info,
		SupportedModes:   SupportedModes(),
		PythonExecutable: p.PythonExecutable(),
	}
	status.Ready = p.runtimeReady()
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
	if strings.TrimSpace(config.DefaultIndex) != "" {
		environment["UV_DEFAULT_INDEX"] = strings.TrimSpace(config.DefaultIndex)
	}
	if config.UseSystemCerts {
		environment["UV_SYSTEM_CERTS"] = "true"
	}
	if strings.TrimSpace(config.HTTPProxy) != "" {
		environment["HTTP_PROXY"] = strings.TrimSpace(config.HTTPProxy)
	}
	if strings.TrimSpace(config.HTTPSProxy) != "" {
		environment["HTTPS_PROXY"] = strings.TrimSpace(config.HTTPSProxy)
	}
	if strings.TrimSpace(config.NoProxy) != "" {
		environment["NO_PROXY"] = strings.TrimSpace(config.NoProxy)
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
		plan.Steps = []Step{
			{Name: "install-python-from-mirror", Executable: uvPath, Arguments: []string{"python", "install", config.PythonVersion, "--install-dir", pythonDir, "--no-progress"}},
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonVersion, "--managed-python"}},
		}
	}
	plan.Steps = append(plan.Steps, Step{
		Name:       "install-data-worker",
		Executable: uvPath,
		Arguments: []string{
			"sync", "--project", filepath.Join(p.runtimeRoot, "worker"), "--locked", "--no-progress",
		},
	})
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
	_ = os.Remove(p.workerMarkerPath())
	for index := range plan.Steps {
		if strings.HasSuffix(plan.Steps[index].Executable, executableName("uv")) {
			plan.Steps[index].Executable = uvPath
		}
		if err := p.runner(ctx, plan.Environment, plan.Steps[index]); err != nil {
			return Result{}, fmt.Errorf("%s: %w", plan.Steps[index].Name, err)
		}
	}
	if err := p.markWorkerReady(); err != nil {
		return Result{}, err
	}

	return Result{
		Mode:             config.Mode,
		PythonExecutable: environmentPython(filepath.Join(p.runtimeRoot, "environments", "data-worker")),
		UVExecutable:     uvPath,
	}, nil
}

func (p *Provisioner) runtimeReady() bool {
	info, err := os.Stat(p.PythonExecutable())
	if err != nil || !info.Mode().IsRegular() {
		return false
	}
	digest, err := p.workerLockDigest()
	if err != nil {
		return false
	}
	marker, err := os.ReadFile(p.workerMarkerPath())
	return err == nil && strings.TrimSpace(string(marker)) == digest
}

func (p *Provisioner) markWorkerReady() error {
	digest, err := p.workerLockDigest()
	if err != nil {
		return fmt.Errorf("fingerprint data worker lockfile: %w", err)
	}
	marker := p.workerMarkerPath()
	if err := os.MkdirAll(filepath.Dir(marker), 0o700); err != nil {
		return fmt.Errorf("create data worker environment directory: %w", err)
	}
	temporary := marker + ".tmp"
	if err := os.WriteFile(temporary, []byte(digest+"\n"), 0o600); err != nil {
		return fmt.Errorf("write data worker installation marker: %w", err)
	}
	if err := os.Rename(temporary, marker); err != nil {
		return fmt.Errorf("publish data worker installation marker: %w", err)
	}
	return nil
}

func (p *Provisioner) workerLockDigest() (string, error) {
	content, err := os.ReadFile(filepath.Join(p.runtimeRoot, "worker", "uv.lock"))
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(content)
	return hex.EncodeToString(digest[:]), nil
}

func (p *Provisioner) workerMarkerPath() string {
	return filepath.Join(p.runtimeRoot, "environments", "data-worker", ".inquira-worker-lock")
}

func (p *Provisioner) PythonExecutable() string {
	return environmentPython(filepath.Join(p.runtimeRoot, "environments", "data-worker"))
}

func (p *Provisioner) Ready() bool { return p.runtimeReady() }

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
