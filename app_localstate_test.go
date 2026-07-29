package main

import (
	"context"
	"errors"
	"testing"

	"github.com/adarsh9780/inquira-ce/internal/localstate"
)

type localStateRecorder struct {
	scope    string
	snapshot localstate.Snapshot
	loaded   localstate.Snapshot
	found    bool
	err      error
}

func (r *localStateRecorder) Save(_ context.Context, scope string, snapshot localstate.Snapshot) error {
	r.scope = scope
	r.snapshot = snapshot
	return r.err
}

func (r *localStateRecorder) Load(_ context.Context, scope string) (localstate.Snapshot, bool, error) {
	r.scope = scope
	return r.loaded, r.found, r.err
}

func (r *localStateRecorder) Close() error { return nil }

func TestNativeLocalStateBridgeSavesAndLoadsSnapshots(t *testing.T) {
	repository := &localStateRecorder{loaded: localstate.Snapshot{"version": float64(1)}, found: true}
	app := &App{localState: repository}
	saved, err := app.SaveLocalState("local-user", localstate.Snapshot{"ui": map[string]any{"terminal_open": true}})
	if err != nil || !saved || repository.scope != "local-user" || repository.snapshot == nil {
		t.Fatalf("SaveLocalState() = %v, %v; recorder = %#v", saved, err, repository)
	}
	loaded, err := app.LoadLocalState("local-user")
	if err != nil || loaded["version"] != float64(1) {
		t.Fatalf("LoadLocalState() = %#v, %v", loaded, err)
	}
}

func TestNativeLocalStateBridgeHandlesMissingStorageAndRepositoryErrors(t *testing.T) {
	if _, err := (&App{}).SaveLocalState("user", localstate.Snapshot{}); err == nil {
		t.Fatal("unavailable local state storage unexpectedly saved")
	}
	repository := &localStateRecorder{err: errors.New("database busy")}
	app := &App{localState: repository}
	if _, err := app.LoadLocalState("user"); err == nil {
		t.Fatal("repository error was not propagated")
	}
}
