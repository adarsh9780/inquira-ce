package main

import (
	"context"
	"errors"
	"path/filepath"
	"testing"

	"inquira-go/internal/appdirs"
	terminalruntime "inquira-go/internal/terminal"
	"inquira-go/internal/workspace"
)

func TestNativeTerminalSessionIsScopedToItsWorkspace(t *testing.T) {
	root := t.TempDir()
	repository, err := workspace.OpenSQLite(filepath.Join(root, "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	workspaces := workspace.NewService(repository)
	created, err := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "Terminal"})
	if err != nil {
		t.Fatal(err)
	}
	app := &App{
		ctx:        context.Background(),
		paths:      appdirs.Paths{DataDir: filepath.Join(root, "data")},
		workspaces: workspaces,
		terminals:  terminalruntime.NewPlatformService(nil),
	}
	t.Cleanup(func() { app.shutdown(context.Background()) })

	if _, err := app.StartTerminalSession(terminalruntime.StartRequest{
		WorkspaceID: created.ID, SessionID: "workspace:another", Cols: 80, Rows: 24,
	}); err == nil {
		t.Fatal("cross-workspace terminal identity unexpectedly succeeded")
	}
	response, err := app.StartTerminalSession(terminalruntime.StartRequest{
		WorkspaceID: created.ID, SessionID: "workspace:" + created.ID, Cwd: root, Cols: 80, Rows: 24,
	})
	if err != nil {
		t.Fatal(err)
	}
	expectedCwd := filepath.Join(root, "data", "workspaces", created.ID)
	if response.Cwd != expectedCwd {
		t.Fatalf("terminal cwd = %q, want %q", response.Cwd, expectedCwd)
	}
	stopped, err := app.StopTerminalSession(response.SessionID)
	if err != nil || !stopped.Stopped {
		t.Fatalf("StopTerminalSession() = %#v, %v", stopped, err)
	}
	if err := app.WriteTerminalSession(response.SessionID, "pwd\n"); !errors.Is(err, terminalruntime.ErrSessionNotFound) {
		t.Fatalf("write after stop error = %v", err)
	}
}
