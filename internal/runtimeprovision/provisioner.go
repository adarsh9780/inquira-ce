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
	"sync"
	"sync/atomic"
	"time"
)

const RuntimeProgressEvent = "runtime-provision-progress"

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
	RepairAvailable    bool         `json:"repairAvailable"`
	RollbackAvailable  bool         `json:"rollbackAvailable"`
	IncompleteSetup    bool         `json:"incompleteSetup"`
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

type Progress struct {
	Operation string `json:"operation"`
	Stage     string `json:"stage"`
	Message   string `json:"message"`
	State     string `json:"state"`
	Current   int    `json:"current"`
	Total     int    `json:"total"`
	Percent   int    `json:"percent"`
}

type ProgressReporter func(Progress)

type DiagnosticPlatform struct {
	OS           string `json:"os"`
	Architecture string `json:"architecture"`
}

type DiagnosticRuntime struct {
	BundleAvailable          bool   `json:"bundleAvailable"`
	Ready                    bool   `json:"ready"`
	OperationActive          bool   `json:"operationActive"`
	RepairAvailable          bool   `json:"repairAvailable"`
	RollbackAvailable        bool   `json:"rollbackAvailable"`
	IncompleteSetup          bool   `json:"incompleteSetup"`
	Mode                     Mode   `json:"mode,omitempty"`
	PythonVersion            string `json:"pythonVersion,omitempty"`
	ExternalPythonConfigured bool   `json:"externalPythonConfigured"`
	SystemCertificates       bool   `json:"systemCertificates"`
	CustomCertificateBundle  bool   `json:"customCertificateBundle"`
}

type DiagnosticUV struct {
	Healthy bool   `json:"healthy"`
	Version string `json:"version,omitempty"`
}

type DiagnosticReport struct {
	SchemaVersion  int                `json:"schemaVersion"`
	GeneratedAtUTC string             `json:"generatedAtUtc"`
	Platform       DiagnosticPlatform `json:"platform"`
	Runtime        DiagnosticRuntime  `json:"runtime"`
	Bundle         BundleInfo         `json:"bundle"`
	UV             DiagnosticUV       `json:"uv"`
	Issues         []string           `json:"issues"`
}

type commandRunner func(context.Context, map[string]string, Step) error

type Provisioner struct {
	runtimeRoot  string
	bundle       fs.FS
	runner       commandRunner
	provisioning atomic.Bool
	cancelMu     sync.Mutex
	cancel       context.CancelFunc
}

func NewProvisioner(runtimeRoot string) *Provisioner {
	return &Provisioner{runtimeRoot: runtimeRoot, bundle: bundledAssets, runner: runStep}
}

func (p *Provisioner) Status() Status {
	info, err := loadBundleInfo(p.bundle)
	if err == nil {
		err = p.validateWorkerContract(info)
	}
	status := Status{
		RuntimeRoot:       p.runtimeRoot,
		Bundle:            info,
		SupportedModes:    SupportedModes(),
		PythonExecutable:  p.PythonExecutable(),
		Provisioning:      p.provisioning.Load(),
		RollbackAvailable: p.runtimeReadyAt(p.previousEnvironmentDir()),
		IncompleteSetup:   pathExists(p.stagingEnvironmentDir()),
	}
	configuration, configurationErr := p.loadConfiguration()
	if configurationErr != nil {
		status.ConfigurationError = configurationErr.Error()
	} else {
		status.Configuration = configuration
		status.RepairAvailable = configuration != nil && configuration.Mode != ModeInternalMirror
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

// DiagnosticReport returns a deliberately bounded, path-free view of runtime
// health. It never includes workspace data, user paths, proxy or mirror URLs,
// package-index values, credentials, or raw command errors.
func (p *Provisioner) DiagnosticReport(ctx context.Context) DiagnosticReport {
	diagnostics := p.Diagnostics(ctx)
	status := diagnostics.Status
	report := DiagnosticReport{
		SchemaVersion:  1,
		GeneratedAtUTC: time.Now().UTC().Format(time.RFC3339),
		Platform: DiagnosticPlatform{
			OS:           runtime.GOOS,
			Architecture: runtime.GOARCH,
		},
		Runtime: DiagnosticRuntime{
			BundleAvailable:   status.BundleAvailable,
			Ready:             status.Ready,
			OperationActive:   status.Provisioning,
			RepairAvailable:   status.RepairAvailable,
			RollbackAvailable: status.RollbackAvailable,
			IncompleteSetup:   status.IncompleteSetup,
		},
		Bundle: status.Bundle,
		UV: DiagnosticUV{
			Healthy: diagnostics.Error == "",
			Version: diagnostics.UVVersion,
		},
		Issues: []string{},
	}
	if status.Configuration != nil {
		report.Runtime.Mode = status.Configuration.Mode
		report.Runtime.PythonVersion = status.Configuration.PythonVersion
		report.Runtime.ExternalPythonConfigured = strings.TrimSpace(status.Configuration.PythonExecutable) != ""
		report.Runtime.SystemCertificates = status.Configuration.UseSystemCerts
		report.Runtime.CustomCertificateBundle = strings.TrimSpace(status.Configuration.CertificateBundle) != ""
	}
	if !status.BundleAvailable {
		report.Issues = append(report.Issues, "embedded-runtime-bundle-unavailable")
	}
	if status.ConfigurationError != "" {
		report.Issues = append(report.Issues, "saved-runtime-configuration-invalid")
	}
	if diagnostics.Error != "" {
		report.Issues = append(report.Issues, "embedded-uv-check-failed")
	}
	return report
}

func (p *Provisioner) Plan(config Config) (Plan, error) {
	if err := config.Validate(); err != nil {
		return Plan{}, err
	}

	uvPath := filepath.Join(p.runtimeRoot, "tools", executableName("uv"))
	pythonDir := filepath.Join(p.runtimeRoot, "python")
	environmentDir := p.stagingEnvironmentDir()
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
	return p.ProvisionWithProgress(ctx, config, nil)
}

func (p *Provisioner) ProvisionWithProgress(ctx context.Context, config Config, reporter ProgressReporter) (result Result, resultErr error) {
	return p.provision(ctx, config, "setup", reporter)
}

func (p *Provisioner) provision(ctx context.Context, config Config, operation string, reporter ProgressReporter) (result Result, resultErr error) {
	if !p.provisioning.CompareAndSwap(false, true) {
		return Result{}, fmt.Errorf("runtime provisioning is already in progress")
	}
	total := 0
	defer func() {
		if resultErr != nil {
			reportProgress(reporter, operation, "failed", operationFailureMessage(operation), "failed", total, total)
		}
	}()
	setupContext, cancel := context.WithCancel(ctx)
	p.cancelMu.Lock()
	p.cancel = cancel
	p.cancelMu.Unlock()
	defer func() {
		cancel()
		p.cancelMu.Lock()
		p.cancel = nil
		p.cancelMu.Unlock()
		p.provisioning.Store(false)
	}()

	plan, err := p.Plan(config)
	if err != nil {
		return Result{}, err
	}
	total = len(plan.Steps) + 3
	reportProgress(reporter, operation, "validate", operationStartMessage(operation), "running", 1, total)
	info, err := loadBundleInfo(p.bundle)
	if err != nil {
		return Result{}, err
	}
	if err := p.validateWorkerContract(info); err != nil {
		return Result{}, err
	}
	uvPath, _, err := extractBundle(p.bundle, filepath.Join(p.runtimeRoot, "tools"))
	if err != nil {
		return Result{}, err
	}
	reportProgress(reporter, operation, "staging", "Preparing an isolated runtime environment.", "running", 2, total)
	if err := p.clearStagingEnvironment(); err != nil {
		return Result{}, err
	}
	activated := false
	defer func() {
		if !activated {
			_ = p.clearStagingEnvironment()
		}
	}()

	for index := range plan.Steps {
		reportProgress(
			reporter,
			operation,
			plan.Steps[index].Name,
			stepProgressMessage(plan.Steps[index].Name),
			"running",
			index+3,
			total,
		)
		if strings.HasSuffix(plan.Steps[index].Executable, executableName("uv")) {
			plan.Steps[index].Executable = uvPath
		}
		if err := p.runner(setupContext, plan.Environment, plan.Steps[index]); err != nil {
			if errors.Is(setupContext.Err(), context.Canceled) {
				return Result{}, fmt.Errorf("runtime setup was cancelled; the previous runtime was left unchanged")
			}
			return Result{}, redactProvisionError(fmt.Errorf("%s: %w", plan.Steps[index].Name, err), config)
		}
	}
	if err := p.markWorkerReadyAt(p.stagingEnvironmentDir()); err != nil {
		return Result{}, err
	}
	if err := p.saveConfigurationAt(p.stagingEnvironmentDir(), config); err != nil {
		return Result{}, err
	}
	reportProgress(reporter, operation, "activate", "Activating the verified runtime.", "running", total, total)
	if err := p.activateStagedEnvironment(); err != nil {
		return Result{}, err
	}
	activated = true

	result = Result{
		Mode:             config.Mode,
		PythonExecutable: p.PythonExecutable(),
		UVExecutable:     uvPath,
	}
	reportProgress(reporter, operation, "complete", operationCompleteMessage(operation), "completed", total, total)
	return result, nil
}

// Cancel stops the active setup command. The previously active environment is
// never modified until the staged environment has passed verification.
func (p *Provisioner) Cancel() bool {
	p.cancelMu.Lock()
	defer p.cancelMu.Unlock()
	if p.cancel == nil {
		return false
	}
	p.cancel()
	return true
}

// Repair rebuilds a runtime from its saved, non-secret configuration. Internal
// mirror credentials are intentionally not persisted, so that mode must be
// re-applied through runtime settings instead.
func (p *Provisioner) Repair(ctx context.Context, reporter ProgressReporter) (Result, error) {
	configuration, err := p.loadConfiguration()
	if err != nil {
		return Result{}, err
	}
	if configuration == nil {
		return Result{}, fmt.Errorf("no saved runtime configuration is available; install the runtime again")
	}
	if configuration.Mode == ModeInternalMirror {
		return Result{}, fmt.Errorf("repairing an internal-mirror runtime requires re-entering mirror and package-index settings")
	}
	config := Config{
		Mode:              configuration.Mode,
		PythonVersion:     configuration.PythonVersion,
		PythonExecutable:  configuration.PythonExecutable,
		UseSystemCerts:    configuration.UseSystemCerts,
		CertificateBundle: configuration.CertificateBundle,
	}
	if config.Mode == ModeManaged && strings.TrimSpace(config.PythonVersion) == "" {
		config.PythonVersion = DefaultConfig().PythonVersion
	}
	return p.provision(ctx, config, "repair", reporter)
}

// Reset removes only Inquira-managed runtime tools, Python installations,
// environments, and legacy runtime configuration. Worker source, workspaces,
// conversations, and connected source files are outside this boundary.
func (p *Provisioner) Reset(reporter ProgressReporter) (resultErr error) {
	if !p.provisioning.CompareAndSwap(false, true) {
		return fmt.Errorf("runtime provisioning is already in progress")
	}
	defer p.provisioning.Store(false)
	targets := []struct {
		stage   string
		message string
		path    string
	}{
		{stage: "remove-environments", message: "Removing installed data environments.", path: filepath.Join(p.runtimeRoot, "environments")},
		{stage: "remove-python", message: "Removing the managed Python installation.", path: filepath.Join(p.runtimeRoot, "python")},
		{stage: "remove-tools", message: "Removing extracted runtime tools.", path: filepath.Join(p.runtimeRoot, "tools")},
		{stage: "remove-legacy-configuration", message: "Removing legacy runtime configuration.", path: p.legacyConfigurationPath()},
	}
	total := len(targets) + 1
	defer func() {
		if resultErr != nil {
			reportProgress(reporter, "reset", "failed", operationFailureMessage("reset"), "failed", total, total)
		}
	}()
	for index, target := range targets {
		reportProgress(reporter, "reset", target.stage, target.message, "running", index+1, total)
		if err := os.RemoveAll(target.path); err != nil {
			return fmt.Errorf("%s: %w", target.stage, err)
		}
	}
	reportProgress(reporter, "reset", "complete", operationCompleteMessage("reset"), "completed", total, total)
	return nil
}

// Rollback swaps the current runtime with the last verified runtime.
func (p *Provisioner) Rollback() (Result, error) {
	return p.RollbackWithProgress(nil)
}

func (p *Provisioner) RollbackWithProgress(reporter ProgressReporter) (result Result, resultErr error) {
	if !p.provisioning.CompareAndSwap(false, true) {
		return Result{}, fmt.Errorf("runtime provisioning is already in progress")
	}
	defer p.provisioning.Store(false)
	const total = 3
	defer func() {
		if resultErr != nil {
			reportProgress(reporter, "rollback", "failed", operationFailureMessage("rollback"), "failed", total, total)
		}
	}()
	reportProgress(reporter, "rollback", "validate", "Checking the previous verified runtime.", "running", 1, total)
	if !p.runtimeReadyAt(p.previousEnvironmentDir()) {
		return Result{}, fmt.Errorf("no verified previous runtime is available")
	}
	reportProgress(reporter, "rollback", "activate", "Restoring the previous verified runtime.", "running", 2, total)
	if err := p.swapActiveAndPrevious(); err != nil {
		return Result{}, err
	}
	configuration, err := p.loadConfiguration()
	if err != nil {
		_ = p.swapActiveAndPrevious()
		return Result{}, fmt.Errorf("load rolled-back runtime configuration: %w", err)
	}
	mode := ModeManaged
	if configuration != nil {
		mode = configuration.Mode
	}
	uvPath, _, err := extractBundle(p.bundle, filepath.Join(p.runtimeRoot, "tools"))
	if err != nil {
		_ = p.swapActiveAndPrevious()
		return Result{}, err
	}
	result = Result{
		Mode:             mode,
		PythonExecutable: p.PythonExecutable(),
		UVExecutable:     uvPath,
	}
	reportProgress(reporter, "rollback", "complete", operationCompleteMessage("rollback"), "completed", total, total)
	return result, nil
}

func reportProgress(reporter ProgressReporter, operation, stage, message, state string, current, total int) {
	if reporter == nil {
		return
	}
	if total < 1 {
		total = 1
	}
	if current < 0 {
		current = 0
	}
	if current > total {
		current = total
	}
	reporter(Progress{
		Operation: operation,
		Stage:     stage,
		Message:   message,
		State:     state,
		Current:   current,
		Total:     total,
		Percent:   current * 100 / total,
	})
}

func stepProgressMessage(stage string) string {
	switch stage {
	case "install-python":
		return "Downloading the approved Python runtime."
	case "install-python-from-mirror":
		return "Downloading approved Python from the internal mirror."
	case "validate-external-python":
		return "Checking the selected company Python."
	case "create-data-environment":
		return "Creating the isolated data environment."
	case "install-data-worker":
		return "Installing the locked data packages."
	case "verify-data-worker":
		return "Verifying the local data worker."
	default:
		return "Preparing the local data runtime."
	}
}

func operationStartMessage(operation string) string {
	if operation == "repair" {
		return "Validating the saved runtime configuration."
	}
	return "Validating the runtime compatibility contract."
}

func operationCompleteMessage(operation string) string {
	switch operation {
	case "repair":
		return "Runtime repair completed."
	case "reset":
		return "Runtime reset completed."
	case "rollback":
		return "Runtime rollback completed."
	default:
		return "Runtime setup completed."
	}
}

func operationFailureMessage(operation string) string {
	switch operation {
	case "repair":
		return "Runtime repair could not be completed."
	case "reset":
		return "Runtime reset could not be completed."
	case "rollback":
		return "Runtime rollback could not be completed."
	default:
		return "Runtime setup could not be completed."
	}
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

const environmentConfigurationFile = ".inquira-runtime-config.json"

func (p *Provisioner) saveConfiguration(config Config) error {
	return p.saveConfigurationAt(p.activeEnvironmentDir(), config)
}

func (p *Provisioner) saveConfigurationAt(environmentDir string, config Config) error {
	content, err := json.MarshalIndent(savedConfigFrom(config), "", "  ")
	if err != nil {
		return fmt.Errorf("encode runtime configuration: %w", err)
	}
	if err := os.MkdirAll(environmentDir, 0o700); err != nil {
		return fmt.Errorf("create runtime environment directory: %w", err)
	}
	path := p.configurationPathAt(environmentDir)
	temporary := path + ".tmp"
	if err := os.WriteFile(temporary, append(content, '\n'), 0o600); err != nil {
		return fmt.Errorf("write runtime configuration: %w", err)
	}
	if err := os.Rename(temporary, path); err != nil {
		return fmt.Errorf("publish runtime configuration: %w", err)
	}
	return nil
}

func (p *Provisioner) loadConfiguration() (*SavedConfig, error) {
	content, err := os.ReadFile(p.configurationPath())
	if errors.Is(err, os.ErrNotExist) {
		content, err = os.ReadFile(p.legacyConfigurationPath())
	}
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
	return p.configurationPathAt(p.activeEnvironmentDir())
}

func (p *Provisioner) configurationPathAt(environmentDir string) string {
	return filepath.Join(environmentDir, environmentConfigurationFile)
}

func (p *Provisioner) legacyConfigurationPath() string {
	return filepath.Join(p.runtimeRoot, "runtime-config.json")
}

func (p *Provisioner) runtimeReady() bool {
	return p.runtimeReadyAt(p.activeEnvironmentDir())
}

func (p *Provisioner) runtimeReadyAt(environmentDir string) bool {
	info, err := os.Stat(environmentPython(environmentDir))
	if err != nil || !info.Mode().IsRegular() {
		return false
	}
	digest, err := p.workerLockDigest()
	if err != nil {
		return false
	}
	marker, err := os.ReadFile(p.workerMarkerPathAt(environmentDir))
	return err == nil && strings.TrimSpace(string(marker)) == digest
}

func (p *Provisioner) markWorkerReady() error {
	return p.markWorkerReadyAt(p.activeEnvironmentDir())
}

func (p *Provisioner) markWorkerReadyAt(environmentDir string) error {
	digest, err := p.workerLockDigest()
	if err != nil {
		return fmt.Errorf("fingerprint data worker lockfile: %w", err)
	}
	marker := p.workerMarkerPathAt(environmentDir)
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

func (p *Provisioner) validateWorkerContract(info BundleInfo) error {
	digest, err := p.workerLockDigest()
	if err != nil {
		return fmt.Errorf("fingerprint data worker lockfile: %w", err)
	}
	if digest != info.WorkerLockSHA256 {
		return fmt.Errorf("bundled data worker does not match the runtime compatibility manifest")
	}
	return nil
}

func (p *Provisioner) workerMarkerPath() string {
	return p.workerMarkerPathAt(p.activeEnvironmentDir())
}

func (p *Provisioner) workerMarkerPathAt(environmentDir string) string {
	return filepath.Join(environmentDir, ".inquira-worker-lock")
}

func (p *Provisioner) PythonExecutable() string {
	return environmentPython(p.activeEnvironmentDir())
}

func (p *Provisioner) Ready() bool { return p.runtimeReady() }

func (p *Provisioner) activeEnvironmentDir() string {
	return filepath.Join(p.runtimeRoot, "environments", "data-worker")
}

func (p *Provisioner) stagingEnvironmentDir() string {
	return filepath.Join(p.runtimeRoot, "environments", "data-worker.staging")
}

func (p *Provisioner) previousEnvironmentDir() string {
	return filepath.Join(p.runtimeRoot, "environments", "data-worker.previous")
}

func (p *Provisioner) clearStagingEnvironment() error {
	if err := os.RemoveAll(p.stagingEnvironmentDir()); err != nil {
		return fmt.Errorf("remove incomplete runtime staging directory: %w", err)
	}
	return nil
}

func (p *Provisioner) activateStagedEnvironment() error {
	staging := p.stagingEnvironmentDir()
	active := p.activeEnvironmentDir()
	previous := p.previousEnvironmentDir()
	if !p.runtimeReadyAt(staging) {
		return fmt.Errorf("staged runtime failed readiness validation")
	}
	if err := os.MkdirAll(filepath.Dir(active), 0o700); err != nil {
		return fmt.Errorf("create runtime environments directory: %w", err)
	}
	if err := os.RemoveAll(previous); err != nil {
		return fmt.Errorf("remove superseded rollback runtime: %w", err)
	}
	hadActive := pathExists(active)
	if hadActive {
		if err := os.Rename(active, previous); err != nil {
			return fmt.Errorf("preserve previous runtime: %w", err)
		}
	}
	if err := os.Rename(staging, active); err != nil {
		if hadActive {
			_ = os.Rename(previous, active)
		}
		return fmt.Errorf("activate staged runtime: %w", err)
	}
	return nil
}

func (p *Provisioner) swapActiveAndPrevious() error {
	active := p.activeEnvironmentDir()
	previous := p.previousEnvironmentDir()
	staging := p.stagingEnvironmentDir()
	if !pathExists(active) {
		return fmt.Errorf("the active runtime is unavailable")
	}
	if err := p.clearStagingEnvironment(); err != nil {
		return err
	}
	if err := os.Rename(active, staging); err != nil {
		return fmt.Errorf("stage current runtime for rollback: %w", err)
	}
	if err := os.Rename(previous, active); err != nil {
		_ = os.Rename(staging, active)
		return fmt.Errorf("activate previous runtime: %w", err)
	}
	if err := os.Rename(staging, previous); err != nil {
		_ = os.Rename(active, previous)
		_ = os.Rename(staging, active)
		return fmt.Errorf("preserve replaced runtime: %w", err)
	}
	return nil
}

func pathExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
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
