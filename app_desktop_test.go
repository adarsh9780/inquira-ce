package main

import (
	"context"
	"encoding/base64"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/wailsapp/wails/v2/pkg/runtime"

	"inquira-go/internal/appdirs"
	"inquira-go/internal/desktop"
)

type desktopCommandRecorder struct {
	name string
	args []string
}

func TestSaveExportFileUsesNativeDialogAndPersistsTheChosenFile(t *testing.T) {
	target := filepath.Join(t.TempDir(), "analysis.csv")
	dialogCalls := 0
	app := &App{saveDialog: func(_ context.Context, options runtime.SaveDialogOptions) (string, error) {
		dialogCalls++
		if options.DefaultFilename != "analysis.csv" || len(options.Filters) != 1 || options.Filters[0].Pattern != "*.csv" {
			t.Fatalf("dialog options = %#v", options)
		}
		return target, nil
	}}
	saved, err := app.SaveExportFile(desktop.ExportRequest{
		DefaultFileName: "analysis.csv",
		ContentBase64:   base64.StdEncoding.EncodeToString([]byte("a,b\n1,2\n")),
		Filters:         []desktop.ExportFilter{{Name: "CSV File", Extensions: []string{"csv"}}},
	})
	if err != nil || !saved || dialogCalls != 1 {
		t.Fatalf("SaveExportFile() = %v, %v; dialog calls = %d", saved, err, dialogCalls)
	}
	contents, err := os.ReadFile(target)
	if err != nil || string(contents) != "a,b\n1,2\n" {
		t.Fatalf("saved export = %q, %v", contents, err)
	}
}

func TestSaveExportFileTreatsAnEmptyDialogPathAsCancellation(t *testing.T) {
	app := &App{saveDialog: func(context.Context, runtime.SaveDialogOptions) (string, error) { return "", nil }}
	saved, err := app.SaveExportFile(desktop.ExportRequest{
		DefaultFileName: "analysis.py",
		ContentBase64:   base64.StdEncoding.EncodeToString([]byte("print('ok')")),
	})
	if err != nil || saved {
		t.Fatalf("SaveExportFile() = %v, %v", saved, err)
	}
}

func TestSaveExportFileValidatesBeforeOpeningDialogAndPropagatesDialogErrors(t *testing.T) {
	dialogCalls := 0
	app := &App{saveDialog: func(context.Context, runtime.SaveDialogOptions) (string, error) {
		dialogCalls++
		return "", errors.New("dialog unavailable")
	}}
	if _, err := app.SaveExportFile(desktop.ExportRequest{DefaultFileName: "../unsafe.csv"}); err == nil || dialogCalls != 0 {
		t.Fatalf("invalid export error = %v; dialog calls = %d", err, dialogCalls)
	}
	_, err := app.SaveExportFile(desktop.ExportRequest{
		DefaultFileName: "analysis.csv",
		ContentBase64:   base64.StdEncoding.EncodeToString([]byte("data")),
	})
	if err == nil || !strings.Contains(err.Error(), "dialog unavailable") || dialogCalls != 1 {
		t.Fatalf("dialog error = %v; dialog calls = %d", err, dialogCalls)
	}
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
