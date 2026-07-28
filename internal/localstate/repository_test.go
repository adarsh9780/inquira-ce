package localstate

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestSQLiteRepositorySavesLoadsAndReplacesScopedSnapshots(t *testing.T) {
	path := filepath.Join(t.TempDir(), "data", "inquira.db")
	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatal(err)
	}
	defer repository.Close()

	first := Snapshot{"version": float64(1), "ui": map[string]any{"active_tab": "workspace"}}
	if err := repository.Save(context.Background(), " User/One ", first); err != nil {
		t.Fatal(err)
	}
	loaded, found, err := repository.Load(context.Background(), "user_one")
	if err != nil || !found || !sameJSON(loaded, first) {
		t.Fatalf("Load() = %#v, %v, %v", loaded, found, err)
	}

	replacement := Snapshot{"version": float64(2), "editor": map[string]any{"generated_code": "print('ok')"}}
	if err := repository.Save(context.Background(), "USER_ONE", replacement); err != nil {
		t.Fatal(err)
	}
	loaded, found, err = repository.Load(context.Background(), "user/one")
	if err != nil || !found || !sameJSON(loaded, replacement) {
		t.Fatalf("replacement Load() = %#v, %v, %v", loaded, found, err)
	}

	missing, found, err := repository.Load(context.Background(), "another-user")
	if err != nil || found || missing != nil {
		t.Fatalf("missing Load() = %#v, %v, %v", missing, found, err)
	}
}

func TestSQLiteRepositoryNormalizesDefaultScopeAndRejectsInvalidSnapshots(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer repository.Close()

	if NormalizeScope("  ") != "default" || NormalizeScope("Team:North@example.com") != "team_north_example_com" {
		t.Fatalf("unexpected normalized scopes: %q, %q", NormalizeScope("  "), NormalizeScope("Team:North@example.com"))
	}
	if err := repository.Save(context.Background(), "default", nil); err == nil {
		t.Fatal("nil snapshot unexpectedly saved")
	}
	if err := repository.Save(context.Background(), "default", Snapshot{"invalid": func() {}}); err == nil {
		t.Fatal("non-JSON snapshot unexpectedly saved")
	}
}

func TestSQLiteRepositoryMigrationAndCorruptPayloadErrors(t *testing.T) {
	root := filepath.Join(t.TempDir(), "private")
	repository, err := OpenSQLite(filepath.Join(root, "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer repository.Close()

	var migrationCount int
	if err := repository.db.QueryRow(`SELECT COUNT(*) FROM schema_migrations WHERE version = 9`).Scan(&migrationCount); err != nil || migrationCount != 1 {
		t.Fatalf("migration 9 count = %d, %v", migrationCount, err)
	}
	if _, err := repository.db.Exec(`INSERT INTO local_state_snapshots(scope, snapshot_json) VALUES ('broken', '{')`); err != nil {
		t.Fatal(err)
	}
	if _, _, err := repository.Load(context.Background(), "broken"); err == nil {
		t.Fatal("corrupt snapshot unexpectedly loaded")
	}
	info, err := os.Stat(root)
	if err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS != "windows" && info.Mode().Perm()&0o077 != 0 {
		t.Fatalf("state directory mode = %#o", info.Mode().Perm())
	}
}

func TestSQLiteSnapshotSurvivesRepositoryReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "inquira.db")
	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatal(err)
	}
	expected := Snapshot{"session": map[string]any{"active_workspace_id": "workspace-1"}}
	if err := repository.Save(context.Background(), "local-user", expected); err != nil {
		t.Fatal(err)
	}
	if err := repository.Close(); err != nil {
		t.Fatal(err)
	}

	reopened, err := OpenSQLite(path)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	loaded, found, err := reopened.Load(context.Background(), "local-user")
	if err != nil || !found || !sameJSON(loaded, expected) {
		t.Fatalf("reopened Load() = %#v, %v, %v", loaded, found, err)
	}
}

func sameJSON(left, right any) bool {
	leftJSON, leftErr := json.Marshal(left)
	rightJSON, rightErr := json.Marshal(right)
	return leftErr == nil && rightErr == nil && string(leftJSON) == string(rightJSON)
}
