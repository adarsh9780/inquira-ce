package runtimeprovision

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync/atomic"
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
	RuntimeRoot        string       `json:"runtimeRoot"`
	BundleAvailable    bool         `json:"bundleAvailable"`
	Bundle             BundleInfo   `json:"bundle"`
	BundleError        string       `json:"bundleError,omitempty"`
	SupportedModes     []Mode       `json:"supportedModes"`
	Ready              bool         `json:"ready"`
	Provisioning       bool         `json:"provisioning"`
	PythonExecutable   string       `json:"pythonExecutable"`
	Configuration      *SavedConfig `json:"configuration,omitempty"`
	ConfigurationError string       `json:"configurationError,omitempty"`
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
	runtimeRoot  string
	bundle       fs.FS
	runner       commandRunner
	provisioning atomic.Bool
}

func NewProvisioner(runtimeRoot string) *Provisioner {
	return &Provisioner{runtimeRoot: runtimeRoot, bundle: bundledAssets, runner: runStep}
}

func (p *Provisioner) Status() Status {
	info, err := loadBundleInfo(p.bundle)
	status := Status{
		RuntimeRoot:      p.runtimeRoot,
		Bundle:           info,
		SupportedModes:   SupportedModes(),
		PythonExecutable: p.PythonExecutable(),
		Provisioning:     p.provisioning.Load(),
	}
	configuration, configurationErr := p.loadConfiguration()
	if configurationErr != nil {
		status.ConfigurationError = configurationErr.Error()
	} else {
		status.Configuration = configuration
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
	uvPath, _, err := extractBundle(p.bundle, filepath.Join(p.runtimeRoot, "tools"))
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
		"UV_NO_CONFIG":           "true",
		"UV_NO_ENV_FILE":         "true",
	}
	if strings.TrimSpace(config.DefaultIndex) != "" {
		environment["UV_DEFAULT_INDEX"] = strings.TrimSpace(config.DefaultIndex)
	}
	if config.UseSystemCerts {
		environment["UV_SYSTEM_CERTS"] = "true"
	}
	if strings.TrimSpace(config.CertificateBundle) != "" {
		environment["SSL_CERT_FILE"] = strings.TrimSpace(config.CertificateBundle)
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
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonVersion, "--managed-python", "--clear"}},
		}
	case ModeExternalPython:
		environment["UV_NO_MANAGED_PYTHON"] = "true"
		plan.Steps = []Step{
			{Name: "validate-external-python", Executable: config.PythonExecutable, Arguments: []string{"-c", "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 'Inquira requires Python 3.12')"}},
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonExecutable, "--no-python-downloads", "--clear"}},
		}
	case ModeInternalMirror:
		environment["UV_PYTHON_INSTALL_MIRROR"] = config.PythonInstallMirror
		plan.Steps = []Step{
			{Name: "install-python-from-mirror", Executable: uvPath, Arguments: []string{"python", "install", config.PythonVersion, "--install-dir", pythonDir, "--no-progress"}},
			{Name: "create-data-environment", Executable: uvPath, Arguments: []string{"venv", environmentDir, "--python", config.PythonVersion, "--managed-python", "--clear"}},
		}
	}
	plan.Steps = append(plan.Steps, Step{
		Name:       "install-data-worker",
		Executable: uvPath,
		Arguments: []string{
			"sync", "--project", filepath.Join(p.runtimeRoot, "worker"), "--locked", "--no-progress",
		},
	})
	plan.Steps = append(plan.Steps, Step{
		Name:       "verify-data-worker",
		Executable: environmentPython(environmentDir),
		Arguments: []string{
			"-c",
			"from inquira_data_worker.runtime import WorkerRuntime; assert callable(WorkerRuntime)",
		},
	})
	return plan, nil
}

// PlanPreview validates a setup request and returns a display-safe plan. It
// never exposes credentials embedded in proxy, mirror, or index URLs.
func (p *Provisioner) PlanPreview(config Config) (Plan, error) {
	plan, err := p.Plan(config)
	if err != nil {
		return Plan{}, err
	}
	for _, key := range []string{"HTTP_PROXY", "HTTPS_PROXY", "UV_DEFAULT_INDEX", "UV_PYTHON_INSTALL_MIRROR"} {
		if value := plan.Environment[key]; value != "" {
			plan.Environment[key] = displaySafeURL(value)
		}
	}
	return plan, nil
}

func (p *Provisioner) Provision(ctx context.Context, config Config) (Result, error) {
	if !p.provisioning.CompareAndSwap(false, true) {
		return Result{}, fmt.Errorf("runtime provisioning is already in progress")
	}
	defer p.provisioning.Store(false)
	plan, err := p.Plan(config)
	if err != nil {
		return Result{}, err
	}
	uvPath, _, err := extractBundle(p.bundle, filepath.Join(p.runtimeRoot, "tools"))
	if err != nil {
		return Result{}, err
	}
	_ = os.Remove(p.workerMarkerPath())
	for index := range plan.Steps {
		if strings.HasSuffix(plan.Steps[index].Executable, executableName("uv")) {
			plan.Steps[index].Executable = uvPath
		}
		if err := p.runner(ctx, plan.Environment, plan.Steps[index]); err != nil {
			return Result{}, redactProvisionError(fmt.Errorf("%s: %w", plan.Steps[index].Name, err), config)
		}
	}
	if err := p.markWorkerReady(); err != nil {
		return Result{}, err
	}
	if err := p.saveConfiguration(config); err != nil {
		_ = os.Remove(p.workerMarkerPath())
		return Result{}, err
	}

	return Result{
		Mode:             config.Mode,
		PythonExecutable: environmentPython(filepath.Join(p.runtimeRoot, "environments", "data-worker")),
		UVExecutable:     uvPath,
	}, nil
}

func redactProvisionError(err error, config Config) error {
	if err == nil {
		return nil
	}
	message := err.Error()
	for _, value := range []string{config.PythonInstallMirror, config.DefaultIndex, config.HTTPProxy, config.HTTPSProxy} {
		normalized := strings.TrimSpace(value)
		if normalized == "" {
			continue
		}
		message = strings.ReplaceAll(message, normalized, displaySafeURL(normalized))
		parsed, parseErr := url.Parse(normalized)
		if parseErr == nil && parsed.User != nil {
			if username := parsed.User.Username(); username != "" {
				message = strings.ReplaceAll(message, username, "[redacted]")
			}
			if password, exists := parsed.User.Password(); exists && password != "" {
				message = strings.ReplaceAll(message, password, "[redacted]")
			}
		}
		if parseErr == nil {
			for _, values := range parsed.Query() {
				for _, secret := range values {
					if secret != "" {
						message = strings.ReplaceAll(message, secret, "[redacted]")
					}
				}
			}
		}
	}
	return errors.New(message)
}

func displaySafeURL(value string) string {
	normalized := strings.TrimSpace(value)
	parsed, err := url.Parse(normalized)
	if err != nil {
		return "[credentials-redacted]"
	}
	if parsed.User == nil && parsed.RawQuery == "" {
		return normalized
	}
	result := parsed.Scheme + "://credentials-redacted@" + parsed.Host + parsed.EscapedPath()
	return result
}

func (p *Provisioner) saveConfiguration(config Config) error {
	content, err := json.MarshalIndent(savedConfigFrom(config), "", "  ")
	if err != nil {
		return fmt.Errorf("encode runtime configuration: %w", err)
	}
	if err := os.MkdirAll(p.runtimeRoot, 0o700); err != nil {
		return fmt.Errorf("create runtime directory: %w", err)
	}
	temporary := p.configurationPath() + ".tmp"
	if err := os.WriteFile(temporary, append(content, '\n'), 0o600); err != nil {
		return fmt.Errorf("write runtime configuration: %w", err)
	}
	if err := os.Rename(temporary, p.configurationPath()); err != nil {
		return fmt.Errorf("publish runtime configuration: %w", err)
	}
	return nil
}

func (p *Provisioner) loadConfiguration() (*SavedConfig, error) {
	content, err := os.ReadFile(p.configurationPath())
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read runtime configuration: %w", err)
	}
	var configuration SavedConfig
	if err := json.Unmarshal(content, &configuration); err != nil {
		return nil, fmt.Errorf("decode runtime configuration: %w", err)
	}
	return &configuration, nil
}

func (p *Provisioner) configurationPath() string {
	return filepath.Join(p.runtimeRoot, "runtime-config.json")
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
