package runtimeprovision

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSupportedModes(t *testing.T) {
	modes := SupportedModes()
	if len(modes) != 3 {
		t.Fatalf("expected three modes, got %d", len(modes))
	}
	if modes[0] != ModeManaged || modes[1] != ModeExternalPython || modes[2] != ModeInternalMirror {
		t.Fatalf("unexpected supported modes: %#v", modes)
	}
}

func TestRuntimeReadinessRequiresTheInstalledWorkerToMatchItsLockfile(t *testing.T) {
	runtimeRoot := filepath.Join(t.TempDir(), "runtime")
	provisioner := NewProvisioner(runtimeRoot)
	if err := os.MkdirAll(filepath.Dir(provisioner.PythonExecutable()), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(provisioner.PythonExecutable(), []byte("python"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(runtimeRoot, "worker"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(runtimeRoot, "worker", "uv.lock"), []byte("version one"), 0o600); err != nil {
		t.Fatal(err)
	}
	if provisioner.runtimeReady() {
		t.Fatal("runtime without a matching installation marker must not be ready")
	}
	if err := provisioner.markWorkerReady(); err != nil {
		t.Fatal(err)
	}
	if !provisioner.runtimeReady() {
		t.Fatal("runtime should be ready after successful worker installation")
	}
	if err := os.WriteFile(filepath.Join(runtimeRoot, "worker", "uv.lock"), []byte("version two"), 0o600); err != nil {
		t.Fatal(err)
	}
	if provisioner.runtimeReady() {
		t.Fatal("runtime must become stale when the bundled worker lockfile changes")
	}
}

func TestRuntimePlanPassesTransientProxyAndNoProxySettings(t *testing.T) {
	provisioner := NewProvisioner(filepath.Join(t.TempDir(), "runtime"))
	config := DefaultConfig()
	config.HTTPProxy = "http://proxy.company:8080"
	config.HTTPSProxy = "https://secure-proxy.company:8443"
	config.NoProxy = "localhost,.company.internal"
	plan, err := provisioner.Plan(config)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Environment["HTTP_PROXY"] != config.HTTPProxy || plan.Environment["HTTPS_PROXY"] != config.HTTPSProxy || plan.Environment["NO_PROXY"] != config.NoProxy {
		t.Fatalf("proxy environment = %#v", plan.Environment)
	}
}

func TestRuntimeConfigRejectsInvalidProxyURLs(t *testing.T) {
	config := DefaultConfig()
	for _, value := range []string{"proxy.company:8080", "ftp://proxy.company", "://bad"} {
		config.HTTPProxy = value
		if err := config.Validate(); err == nil {
			t.Fatalf("expected proxy %q to be rejected", value)
		}
	}
}

func TestExternalPythonRequiresExecutable(t *testing.T) {
	config := DefaultConfig()
	config.Mode = ModeExternalPython
	if err := config.Validate(); err == nil {
		t.Fatal("expected external mode without an executable to fail")
	}
}

func TestInternalMirrorRequiresBothMirrors(t *testing.T) {
	config := DefaultConfig()
	config.Mode = ModeInternalMirror
	config.PythonInstallMirror = "https://packages.example/python"
	if err := config.Validate(); err == nil {
		t.Fatal("expected internal mirror mode without a package index to fail")
	}
	config.DefaultIndex = "https://packages.example/pypi/simple"
	if err := config.Validate(); err != nil {
		t.Fatalf("expected complete internal mirror config to pass: %v", err)
	}
}

func TestPlansKeepExternalModeOfflineAndMirrorModePrivate(t *testing.T) {
	provisioner := NewProvisioner(filepath.Join(t.TempDir(), "runtime"))

	external := DefaultConfig()
	external.Mode = ModeExternalPython
	external.PythonExecutable = "/company/python"
	externalPlan, err := provisioner.Plan(external)
	if err != nil {
		t.Fatal(err)
	}
	if externalPlan.Environment["UV_NO_MANAGED_PYTHON"] != "true" {
		t.Fatal("external mode must disable managed Python downloads")
	}
	if got := externalPlan.Steps[1].Arguments[len(externalPlan.Steps[1].Arguments)-1]; got != "--no-python-downloads" {
		t.Fatalf("external environment may not download Python, got final argument %q", got)
	}

	mirror := DefaultConfig()
	mirror.Mode = ModeInternalMirror
	mirror.PythonInstallMirror = "https://packages.example/python"
	mirror.DefaultIndex = "https://packages.example/pypi/simple"
	mirror.UseSystemCerts = true
	mirrorPlan, err := provisioner.Plan(mirror)
	if err != nil {
		t.Fatal(err)
	}
	if mirrorPlan.Environment["UV_PYTHON_INSTALL_MIRROR"] != mirror.PythonInstallMirror {
		t.Fatal("internal mirror was not passed to UV")
	}
	if mirrorPlan.Environment["UV_DEFAULT_INDEX"] != mirror.DefaultIndex {
		t.Fatal("private package index was not passed to UV")
	}
	if mirrorPlan.Environment["UV_SYSTEM_CERTS"] != "true" {
		t.Fatal("system certificates were not enabled")
	}
}

func TestEveryRuntimePlanInstallsTheBundledDataWorkerIntoTheEnvironment(t *testing.T) {
	runtimeRoot := filepath.Join(t.TempDir(), "runtime")
	provisioner := NewProvisioner(runtimeRoot)
	configs := []Config{DefaultConfig()}
	external := DefaultConfig()
	external.Mode = ModeExternalPython
	external.PythonExecutable = "/company/python"
	external.DefaultIndex = "https://packages.example/simple"
	configs = append(configs, external)
	mirror := DefaultConfig()
	mirror.Mode = ModeInternalMirror
	mirror.PythonInstallMirror = "https://packages.example/python"
	mirror.DefaultIndex = "https://packages.example/simple"
	configs = append(configs, mirror)

	for _, config := range configs {
		plan, err := provisioner.Plan(config)
		if err != nil {
			t.Fatal(err)
		}
		last := plan.Steps[len(plan.Steps)-1]
		if last.Name != "install-data-worker" || last.Executable != filepath.Join(runtimeRoot, "tools", executableName("uv")) {
			t.Fatalf("%s final step = %#v", config.Mode, last)
		}
		if got := plan.Environment["UV_PROJECT_ENVIRONMENT"]; got != filepath.Join(runtimeRoot, "environments", "data-worker") {
			t.Fatalf("%s environment = %q", config.Mode, got)
		}
		if config.DefaultIndex != "" && plan.Environment["UV_DEFAULT_INDEX"] != config.DefaultIndex {
			t.Fatalf("%s private index not applied", config.Mode)
		}
	}
}
