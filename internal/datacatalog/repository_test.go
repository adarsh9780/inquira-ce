package datacatalog

import (
	"context"
	"path/filepath"
	"testing"

	"github.com/adarsh9780/inquira-ce/internal/workspace"
)

func TestSQLiteSchemaRepositoryPersistsReplacementsAndCascadesWithWorkspace(t *testing.T) {
	database := filepath.Join(t.TempDir(), "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	workspaces := workspace.NewService(workspaceRepository)
	created, err := workspaces.Create(context.Background(), workspace.CreateRequest{Name: "Analysis"})
	if err != nil {
		t.Fatal(err)
	}

	repository, err := OpenSQLite(database)
	if err != nil {
		t.Fatal(err)
	}
	if err := repository.Replace(context.Background(), created.ID, "sales", []ColumnOverride{{Name: "amount", Description: "Revenue", Aliases: []string{"sales", "bookings"}}}); err != nil {
		t.Fatal(err)
	}
	loaded, err := repository.List(context.Background(), created.ID, "sales")
	if err != nil || len(loaded) != 1 || loaded[0].Aliases[1] != "bookings" {
		t.Fatalf("List() = %#v, %v", loaded, err)
	}
	if err := repository.Replace(context.Background(), created.ID, "sales", nil); err != nil {
		t.Fatal(err)
	}
	loaded, err = repository.List(context.Background(), created.ID, "sales")
	if err != nil || len(loaded) != 0 {
		t.Fatalf("replacement did not clear rows: %#v, %v", loaded, err)
	}
	if err := repository.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := workspaces.Delete(context.Background(), created.ID); err != nil {
		t.Fatal(err)
	}
	if err := workspaces.Close(); err != nil {
		t.Fatal(err)
	}
}
