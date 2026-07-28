package runtimeprovision

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFailedStagedProvisioningPreservesTheActiveRuntime(t *testing.T) {
	provisioner := newLifecycleProvisioner(t)
	writeVerifiedEnvironment(t, provisioner, provisioner.activeEnvironmentDir(), Config{
		Mode:             ModeExternalPython,
		PythonExecutable: "/previous/python",
	})
	provisioner.runner = func(_ context.Context, _ map[string]string, step Step) error {
		if step.Name == "verify-data-worker" {
			return errors.New("worker import failed")
		}
		return nil
	}

	if _, err := provisioner.Provision(t.Context(), DefaultConfig()); err == nil {
		t.Fatal("expected staged verification to fail")
	}
	if !provisioner.Ready() {
		t.Fatal("the active runtime must remain ready after a staged failure")
	}
	configuration, err := provisioner.loadConfiguration()
	if err != nil {
		t.Fatal(err)
	}
	if configuration == nil || configuration.Mode != ModeExternalPython {
		t.Fatalf("active configuration changed after failed setup: %#v", configuration)
	}
	if pathExists(provisioner.stagingEnvironmentDir()) {
		t.Fatal("failed staging environment was not cleaned up")
	}
}

func TestSuccessfulProvisioningActivatesAtomicallyAndSupportsRollback(t *testing.T) {
	provisioner := newLifecycleProvisioner(t)
	writeVerifiedEnvironment(t, provisioner, provisioner.activeEnvironmentDir(), Config{
		Mode:             ModeExternalPython,
		PythonExecutable: "/previous/python",
	})
	provisioner.runner = func(_ context.Context, _ map[string]string, step Step) error {
		if step.Name == "create-data-environment" {
			writeEnvironmentPython(t, provisioner.stagingEnvironmentDir(), "new python")
		}
		return nil
	}

	result, err := provisioner.Provision(t.Context(), DefaultConfig())
	if err != nil {
		t.Fatal(err)
	}
	if result.Mode != ModeManaged || !provisioner.Ready() {
		t.Fatalf("new runtime was not activated: result=%#v status=%#v", result, provisioner.Status())
	}
	status := provisioner.Status()
	if !status.RollbackAvailable {
		t.Fatal("the previous verified runtime was not retained")
	}
	if status.Configuration == nil || status.Configuration.Mode != ModeManaged {
		t.Fatalf("new runtime configuration = %#v", status.Configuration)
	}

	rolledBack, err := provisioner.Rollback()
	if err != nil {
		t.Fatal(err)
	}
	if rolledBack.Mode != ModeExternalPython || !provisioner.Ready() {
		t.Fatalf("previous runtime was not restored: result=%#v status=%#v", rolledBack, provisioner.Status())
	}
	configuration, err := provisioner.loadConfiguration()
	if err != nil {
		t.Fatal(err)
	}
	if configuration == nil || configuration.Mode != ModeExternalPython {
		t.Fatalf("rolled-back configuration = %#v", configuration)
	}
	if !provisioner.Status().RollbackAvailable {
		t.Fatal("rollback should remain reversible")
	}
}

func TestCancelledProvisioningLeavesThePreviousRuntimeReady(t *testing.T) {
	provisioner := newLifecycleProvisioner(t)
	writeVerifiedEnvironment(t, provisioner, provisioner.activeEnvironmentDir(), DefaultConfig())
	started := make(chan struct{})
	provisioner.runner = func(ctx context.Context, _ map[string]string, _ Step) error {
		select {
		case <-started:
		default:
			close(started)
		}
		<-ctx.Done()
		return ctx.Err()
	}
	result := make(chan error, 1)
	go func() {
		_, err := provisioner.Provision(context.Background(), DefaultConfig())
		result <- err
	}()
	<-started
	if !provisioner.Cancel() {
		t.Fatal("active setup was not cancelled")
	}
	err := <-result
	if err == nil || !strings.Contains(err.Error(), "cancelled") {
		t.Fatalf("cancelled setup error = %v", err)
	}
	if !provisioner.Ready() {
		t.Fatal("the previous runtime must remain ready after cancellation")
	}
	if pathExists(provisioner.stagingEnvironmentDir()) {
		t.Fatal("cancelled staging environment was not cleaned up")
	}
}

func TestStatusReportsAnIncompleteStagingEnvironment(t *testing.T) {
	provisioner := newLifecycleProvisioner(t)
	if err := os.MkdirAll(provisioner.stagingEnvironmentDir(), 0o700); err != nil {
		t.Fatal(err)
	}
	if !provisioner.Status().IncompleteSetup {
		t.Fatal("incomplete setup was not reported")
	}
}

func newLifecycleProvisioner(t *testing.T) *Provisioner {
	t.Helper()
	workerLock := []byte("locked worker")
	lockDigest := sha256.Sum256(workerLock)
	provisioner := NewProvisioner(filepath.Join(t.TempDir(), "runtime"))
	provisioner.bundle = testBundleFS(t, hex.EncodeToString(lockDigest[:]))
	if err := os.MkdirAll(filepath.Join(provisioner.runtimeRoot, "worker"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(provisioner.runtimeRoot, "worker", "uv.lock"), workerLock, 0o600); err != nil {
		t.Fatal(err)
	}
	return provisioner
}

func writeVerifiedEnvironment(t *testing.T, provisioner *Provisioner, environmentDir string, config Config) {
	t.Helper()
	writeEnvironmentPython(t, environmentDir, "verified python")
	if err := provisioner.markWorkerReadyAt(environmentDir); err != nil {
		t.Fatal(err)
	}
	if err := provisioner.saveConfigurationAt(environmentDir, config); err != nil {
		t.Fatal(err)
	}
}

func writeEnvironmentPython(t *testing.T, environmentDir, content string) {
	t.Helper()
	python := environmentPython(environmentDir)
	if err := os.MkdirAll(filepath.Dir(python), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(python, []byte(content), 0o700); err != nil {
		t.Fatal(err)
	}
}
