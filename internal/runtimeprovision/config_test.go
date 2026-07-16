package runtimeprovision

import (
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
