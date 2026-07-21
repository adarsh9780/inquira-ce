package runtimeprovision

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestManagedRuntimeOnlyAcceptsWorkerCompatiblePython(t *testing.T) {
	for _, version := range []string{"", "3.11", "3.13", "python3.12", "3.12-rc"} {
		config := DefaultConfig()
		config.PythonVersion = version
		if err := config.Validate(); err == nil {
			t.Fatalf("expected incompatible Python version %q to be rejected", version)
		}
	}
	for _, version := range []string{"3.12", "3.12.9"} {
		config := DefaultConfig()
		config.PythonVersion = version
		if err := config.Validate(); err != nil {
			t.Fatalf("expected Python version %q to pass: %v", version, err)
		}
	}
}

func TestExternalPythonMustBeAnAbsoluteExecutableFile(t *testing.T) {
	config := DefaultConfig()
	config.Mode = ModeExternalPython
	for _, path := range []string{"python3.12", filepath.Join(t.TempDir(), "missing-python")} {
		config.PythonExecutable = path
		if err := config.Validate(); err == nil {
			t.Fatalf("expected external Python path %q to be rejected", path)
		}
	}

	path := filepath.Join(t.TempDir(), executableName("python"))
	mode := os.FileMode(0o700)
	if runtime.GOOS == "windows" {
		mode = 0o600
	}
	if err := os.WriteFile(path, []byte("python"), mode); err != nil {
		t.Fatal(err)
	}
	config.PythonExecutable = path
	if err := config.Validate(); err != nil {
		t.Fatalf("expected executable Python path to pass: %v", err)
	}
	plan, err := NewProvisioner(filepath.Join(t.TempDir(), "runtime")).Plan(config)
	if err != nil {
		t.Fatal(err)
	}
	validation := plan.Steps[0]
	if validation.Name != "validate-external-python" || len(validation.Arguments) != 2 || validation.Arguments[0] != "-c" || !strings.Contains(validation.Arguments[1], "(3, 12)") {
		t.Fatalf("external Python compatibility step = %#v", validation)
	}
}

func TestRuntimeConfigValidatesMirrorIndexAndCertificateBundle(t *testing.T) {
	config := DefaultConfig()
	config.Mode = ModeInternalMirror
	config.PythonInstallMirror = "packages.company/python"
	config.DefaultIndex = "ftp://packages.company/simple"
	if err := config.Validate(); err == nil {
		t.Fatal("expected invalid mirror and index URLs to be rejected")
	}

	config.PythonInstallMirror = "https://packages.company/python"
	config.DefaultIndex = "https://packages.company/simple"
	config.CertificateBundle = filepath.Join(t.TempDir(), "missing.pem")
	if err := config.Validate(); err == nil {
		t.Fatal("expected a missing certificate bundle to be rejected")
	}
	if err := os.WriteFile(config.CertificateBundle, []byte("certificate"), 0o600); err != nil {
		t.Fatal(err)
	}
	plan, err := NewProvisioner(filepath.Join(t.TempDir(), "runtime")).Plan(config)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Environment["SSL_CERT_FILE"] != config.CertificateBundle {
		t.Fatalf("custom certificate bundle not passed to UV: %#v", plan.Environment)
	}
}

func TestRuntimePlanPreviewAndErrorsRedactCredentialBearingURLs(t *testing.T) {
	config := DefaultConfig()
	config.DefaultIndex = "https://index-user:index-password@packages.company/simple?token=index-token"
	config.HTTPProxy = "http://proxy-user:proxy-password@proxy.company:8080"
	provisioner := NewProvisioner(filepath.Join(t.TempDir(), "runtime"))
	preview, err := provisioner.PlanPreview(config)
	if err != nil {
		t.Fatal(err)
	}
	serialized, err := json.Marshal(preview)
	if err != nil {
		t.Fatal(err)
	}
	for _, secret := range []string{"index-user", "index-password", "index-token", "proxy-user", "proxy-password"} {
		if strings.Contains(string(serialized), secret) {
			t.Fatalf("plan preview leaked %q: %s", secret, serialized)
		}
	}
	if !strings.Contains(string(serialized), "credentials-redacted") {
		t.Fatalf("plan preview should identify redacted URLs: %s", serialized)
	}

	redacted := redactProvisionError(errors.New("failed to reach "+config.DefaultIndex+" through "+config.HTTPProxy), config)
	for _, secret := range []string{"index-password", "index-token", "proxy-password"} {
		if strings.Contains(redacted.Error(), secret) {
			t.Fatalf("provisioning error leaked %q: %v", secret, redacted)
		}
	}
}

func TestSavedRuntimeConfigurationExcludesTransientNetworkCredentials(t *testing.T) {
	runtimeRoot := filepath.Join(t.TempDir(), "runtime")
	provisioner := NewProvisioner(runtimeRoot)
	config := DefaultConfig()
	config.DefaultIndex = "https://user:password@packages.company/simple"
	config.HTTPProxy = "http://user:password@proxy.company:8080"
	config.NoProxy = "localhost"
	config.UseSystemCerts = true
	if err := provisioner.saveConfiguration(config); err != nil {
		t.Fatal(err)
	}
	content, err := os.ReadFile(provisioner.configurationPath())
	if err != nil {
		t.Fatal(err)
	}
	for _, forbidden := range []string{"packages.company", "proxy.company", "password", "localhost"} {
		if strings.Contains(string(content), forbidden) {
			t.Fatalf("saved runtime configuration leaked transient value %q: %s", forbidden, content)
		}
	}
	status := provisioner.Status()
	if status.Configuration == nil || status.Configuration.Mode != ModeManaged || !status.Configuration.UseSystemCerts {
		t.Fatalf("safe runtime configuration was not restored: %#v", status.Configuration)
	}
}

func TestConcurrentRuntimeProvisioningIsRejectedBeforeMachineChanges(t *testing.T) {
	provisioner := NewProvisioner(filepath.Join(t.TempDir(), "runtime"))
	provisioner.provisioning.Store(true)
	_, err := provisioner.Provision(t.Context(), DefaultConfig())
	if err == nil || !strings.Contains(err.Error(), "already in progress") {
		t.Fatalf("expected concurrent setup to be rejected, got %v", err)
	}
}

func TestFailedWorkerVerificationDoesNotMarkRuntimeReady(t *testing.T) {
	runtimeRoot := filepath.Join(t.TempDir(), "runtime")
	provisioner := NewProvisioner(runtimeRoot)
	config := DefaultConfig()
	config.Mode = ModeExternalPython
	config.PythonExecutable = testPythonExecutable(t)
	if err := os.MkdirAll(filepath.Join(runtimeRoot, "worker"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(runtimeRoot, "worker", "uv.lock"), []byte("lock"), 0o600); err != nil {
		t.Fatal(err)
	}

	var steps []string
	provisioner.runner = func(_ context.Context, _ map[string]string, step Step) error {
		steps = append(steps, step.Name)
		if step.Name == "verify-data-worker" {
			return errors.New("worker import failed")
		}
		return nil
	}
	_, err := provisioner.Provision(t.Context(), config)
	if err == nil || !strings.Contains(err.Error(), "verify-data-worker") {
		t.Fatalf("verification error = %v", err)
	}
	if len(steps) == 0 || steps[len(steps)-1] != "verify-data-worker" {
		t.Fatalf("executed steps = %#v", steps)
	}
	if provisioner.Ready() {
		t.Fatal("a runtime with a failed worker verification must not be ready")
	}
}
