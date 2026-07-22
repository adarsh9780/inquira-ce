package main

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"inquira-go/internal/appdirs"
	"inquira-go/internal/desktop"
)

type desktopCommandRecorder struct {
	name string
	args []string
}

func (r *desktopCommandRecorder) Start(name string, args ...string) error {
	r.name = name
	r.args = append([]string(nil), args...)
	return nil
}

func TestStartupStateReflectsNativeInitializationResult(t *testing.T) {
	ready := (&App{}).GetStartupState()
	if !ready.Ready || ready.Error != "" {
		t.Fatalf("ready startup state = %#v", ready)
	}
	failed := (&App{initErr: errors.New("database unavailable")}).GetStartupState()
	if failed.Ready || !strings.Contains(failed.Error, "database unavailable") {
		t.Fatalf("failed startup state = %#v", failed)
	}
}

func TestStartupRecoveryWritesAndOpensPrivateDiagnostics(t *testing.T) {
	recorder := &desktopCommandRecorder{}
	logs := filepath.Join(t.TempDir(), "logs")
	app := &App{
		paths:   appdirs.Paths{LogsDir: logs},
		desktop: desktop.NewService(desktop.Config{Platform: "darwin", Starter: recorder}),
		initErr: errors.New("database unavailable"),
	}
	app.GetStartupState()
	if err := app.OpenStartupLogs(); err != nil {
		t.Fatal(err)
	}
	contents, err := os.ReadFile(filepath.Join(logs, desktop.StartupLogName))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(contents), "database unavailable") || recorder.name != "open" || len(recorder.args) != 1 || recorder.args[0] != logs {
		t.Fatalf("diagnostics = %q; launcher = %q %#v", contents, recorder.name, recorder.args)
	}
}

func TestFallbackStartupLogDirectoryIsPrivate(t *testing.T) {
	directory, err := createFallbackStartupLogDirectory(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(directory)
	if err != nil {
		t.Fatal(err)
	}
	if !info.IsDir() || info.Mode().Perm()&0o077 != 0 {
		t.Fatalf("fallback log mode = %v", info.Mode())
	}
}
