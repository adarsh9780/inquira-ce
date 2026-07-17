package workspace

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"

	"inquira-go/internal/apperror"
)

func TestWorkspaceLifecyclePersistsAndMaintainsOneActiveWorkspace(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "inquira.db")
	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatalf("OpenSQLite() error = %v", err)
	}
	service := NewService(repository)
	clock := time.Date(2026, 7, 17, 8, 0, 0, 0, time.UTC)
	service.now = func() time.Time {
		clock = clock.Add(time.Second)
		return clock
	}
	ctx := context.Background()

	first, err := service.Create(ctx, CreateRequest{Name: "  Sales  ", SchemaContext: "Revenue definitions"})
	if err != nil {
		t.Fatalf("Create(first) error = %v", err)
	}
	if first.Name != "Sales" || !first.IsActive || first.SchemaContext != "Revenue definitions" {
		t.Fatalf("first workspace = %#v", first)
	}
	second, err := service.Create(ctx, CreateRequest{Name: "Operations"})
	if err != nil {
		t.Fatalf("Create(second) error = %v", err)
	}
	if second.IsActive {
		t.Fatal("second workspace should not replace the active workspace")
	}
	activated, err := service.Activate(ctx, second.ID)
	if err != nil || !activated.IsActive {
		t.Fatalf("Activate() = %#v, %v", activated, err)
	}
	contextUpdate := "Updated operational context"
	updated, err := service.Update(ctx, UpdateRequest{
		WorkspaceID: second.ID, Name: "Operations 2026", SchemaContext: &contextUpdate,
	})
	if err != nil {
		t.Fatalf("Update() error = %v", err)
	}
	if updated.Name != "Operations 2026" || updated.SchemaContext != contextUpdate {
		t.Fatalf("updated workspace = %#v", updated)
	}

	if err := service.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := OpenSQLite(path)
	if err != nil {
		t.Fatalf("reopen error = %v", err)
	}
	service = NewService(reopened)
	defer service.Close()
	listed, err := service.List(ctx)
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
	if len(listed.Workspaces) != 2 || listed.Workspaces[0].ID != second.ID || !listed.Workspaces[0].IsActive {
		t.Fatalf("persisted workspaces = %#v", listed.Workspaces)
	}

	if _, err := service.Delete(ctx, second.ID); err != nil {
		t.Fatalf("Delete(active) error = %v", err)
	}
	listed, err = service.List(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(listed.Workspaces) != 1 || listed.Workspaces[0].ID != first.ID || !listed.Workspaces[0].IsActive {
		t.Fatalf("fallback workspace = %#v", listed.Workspaces)
	}
}

func TestWorkspaceNamesAreValidatedAndCaseInsensitiveUnique(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository)
	defer service.Close()
	ctx := context.Background()

	if _, err := service.Create(ctx, CreateRequest{Name: "   "}); errorCode(err) != "workspace_name_required" {
		t.Fatalf("blank name error = %v", err)
	}
	if _, err := service.Create(ctx, CreateRequest{Name: "Quarterly   Results"}); err != nil {
		t.Fatal(err)
	}
	if _, err := service.Create(ctx, CreateRequest{Name: " quarterly results "}); errorCode(err) != "workspace_name_exists" {
		t.Fatalf("duplicate name error = %v", err)
	}
}

func TestWorkspaceSummaryDefersDataCounts(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository)
	defer service.Close()
	created, err := service.Create(context.Background(), CreateRequest{Name: "Research"})
	if err != nil {
		t.Fatal(err)
	}
	summary, err := service.Summary(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if summary.TableCount != 0 || summary.ConversationCount != 0 || summary.TableNames == nil {
		t.Fatalf("summary = %#v", summary)
	}
}

func TestDeletingLastWorkspaceLetsNextWorkspaceBecomeActive(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository)
	defer service.Close()
	ctx := context.Background()
	first, err := service.Create(ctx, CreateRequest{Name: "First"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := service.Delete(ctx, first.ID); err != nil {
		t.Fatal(err)
	}
	second, err := service.Create(ctx, CreateRequest{Name: "Second"})
	if err != nil {
		t.Fatal(err)
	}
	if !second.IsActive {
		t.Fatal("workspace created after deleting the last workspace should be active")
	}
}

func errorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
