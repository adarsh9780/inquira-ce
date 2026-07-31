package datacatalog

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/adarsh9780/inquira-ce/internal/apperror"
	"github.com/adarsh9780/inquira-ce/internal/connection"
	"github.com/adarsh9780/inquira-ce/internal/workspace"
)

type fakeWorkspaces struct {
	summary workspace.Summary
	err     error
}

func errorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}

func (f fakeWorkspaces) Summary(context.Context, string) (workspace.Summary, error) {
	return f.summary, f.err
}

type fakeConnections struct {
	response connection.ListResponse
	err      error
}

func (f fakeConnections) List(context.Context, string) (connection.ListResponse, error) {
	return f.response, f.err
}

type fakeCatalogGateway struct {
	mu          sync.Mutex
	request     BuildRequest
	result      BuildResult
	err         error
	calls       int
	started     chan struct{}
	continueRun chan struct{}
}

type fakeSchemaRepository struct {
	items    map[string][]ColumnOverride
	contexts map[string]string
}

func (f *fakeSchemaRepository) List(_ context.Context, workspaceID, tableName string) ([]ColumnOverride, error) {
	return append([]ColumnOverride(nil), f.items[workspaceID+"/"+tableName]...), nil
}

func (f *fakeSchemaRepository) TableContext(_ context.Context, workspaceID, tableName string) (string, error) {
	return f.contexts[workspaceID+"/"+tableName], nil
}

func (f *fakeSchemaRepository) Replace(_ context.Context, workspaceID, tableName string, tableContext *string, items []ColumnOverride) error {
	if f.items == nil {
		f.items = map[string][]ColumnOverride{}
	}
	key := workspaceID + "/" + tableName
	f.items[key] = append([]ColumnOverride(nil), items...)
	if tableContext != nil {
		if f.contexts == nil {
			f.contexts = map[string]string{}
		}
		f.contexts[key] = *tableContext
	}
	return nil
}

func (f *fakeSchemaRepository) Close() error { return nil }

func (f *fakeCatalogGateway) Build(_ context.Context, request BuildRequest) (BuildResult, error) {
	f.mu.Lock()
	f.calls++
	f.request = request
	started, continueRun := f.started, f.continueRun
	result, err := f.result, f.err
	if result.DatabasePath == "" {
		result.DatabasePath = request.DatabasePath
	}
	if result.Fingerprint == "" {
		result.Fingerprint = request.Fingerprint
	}
	if result.TableCount == 0 && len(request.Tables) > 0 {
		result.TableCount = len(request.Tables)
	}
	f.mu.Unlock()
	if started != nil {
		started <- struct{}{}
	}
	if continueRun != nil {
		<-continueRun
	}
	return result, err
}

func snapshot(t *testing.T, name string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), name+".parquet")
	if err := os.WriteFile(path, []byte("parquet"), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestPrepareBuildsStableAnalysisTablesFromEveryConnectionOutput(t *testing.T) {
	connections := connection.ListResponse{Connections: []connection.Connection{
		{ID: "connection-1", Name: "Sales Data", Status: connection.StatusReady, SourceFingerprint: "one", Outputs: []connection.Output{
			{SourceObjectID: "file", Name: "sales", SnapshotPath: snapshot(t, "sales"), RowCount: 3, Columns: []connection.Column{{Name: "id", DataType: "BIGINT"}}},
		}},
		{ID: "connection-2", Name: "Workbook", Status: connection.StatusNeedsAttention, SourceFingerprint: "two", Outputs: []connection.Output{
			{SourceObjectID: "sheet:North", Name: "North", SnapshotPath: snapshot(t, "north"), RowCount: 2},
			{SourceObjectID: "sheet:South", Name: "South", SnapshotPath: snapshot(t, "south"), RowCount: 4},
		}},
	}}
	gateway := &fakeCatalogGateway{result: BuildResult{Changed: true, ByteSize: 100}}
	service := NewService(
		fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}},
		fakeConnections{response: connections}, gateway, t.TempDir(),
	)

	result, err := service.Prepare(context.Background(), "workspace-1")
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Tables) != 3 {
		t.Fatalf("tables = %#v", result.Tables)
	}
	if result.Tables[0].Name != "sales_data" || result.Tables[1].Name != "workbook_north" || result.Tables[2].Name != "workbook_south" {
		t.Fatalf("table names = %#v", result.Tables)
	}
	if result.Tables[1].Status != TableStatusStale || result.Tables[0].Status != TableStatusReady {
		t.Fatalf("table statuses = %#v", result.Tables)
	}
	if result.Tables[0].ID == "" || result.Tables[0].ID == result.Tables[1].ID || result.Fingerprint == "" {
		t.Fatalf("unstable identifiers: %#v", result)
	}
	if gateway.request.DatabasePath != result.DatabasePath || len(gateway.request.Tables) != 3 {
		t.Fatalf("build request = %#v", gateway.request)
	}
}

func TestPrepareDisambiguatesNormalizedTableNameCollisionsDeterministically(t *testing.T) {
	connections := connection.ListResponse{Connections: []connection.Connection{
		{ID: "a", Name: "Sales-data", SourceFingerprint: "one", Outputs: []connection.Output{{SourceObjectID: "file", Name: "a", SnapshotPath: snapshot(t, "a")}}},
		{ID: "b", Name: "Sales data", SourceFingerprint: "two", Outputs: []connection.Output{{SourceObjectID: "file", Name: "b", SnapshotPath: snapshot(t, "b")}}},
	}}
	gateway := &fakeCatalogGateway{}
	service := NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}}, fakeConnections{response: connections}, gateway, t.TempDir())
	first, err := service.Prepare(context.Background(), "workspace-1")
	if err != nil {
		t.Fatal(err)
	}
	second, err := service.Prepare(context.Background(), "workspace-1")
	if err != nil {
		t.Fatal(err)
	}
	if first.Tables[0].Name != "sales_data" || first.Tables[1].Name == "sales_data" || first.Tables[1].Name != second.Tables[1].Name {
		t.Fatalf("collision names = %#v / %#v", first.Tables, second.Tables)
	}
}

func TestPrepareSupportsAnEmptyWorkspaceAndRejectsMissingSnapshots(t *testing.T) {
	gateway := &fakeCatalogGateway{}
	root := t.TempDir()
	service := NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}}, fakeConnections{}, gateway, root)
	result, err := service.Prepare(context.Background(), "workspace-1")
	if err != nil || len(result.Tables) != 0 || gateway.calls != 1 {
		t.Fatalf("empty catalog = %#v, %v", result, err)
	}

	missing := filepath.Join(root, "missing.parquet")
	service = NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}}, fakeConnections{response: connection.ListResponse{Connections: []connection.Connection{{
		ID: "connection", Name: "Missing", Outputs: []connection.Output{{SourceObjectID: "file", SnapshotPath: missing}},
	}}}}, gateway, root)
	if _, err := service.Prepare(context.Background(), "workspace-1"); errorCode(err) != "catalog_snapshot_missing" {
		t.Fatalf("missing snapshot error = %v", err)
	}
	if gateway.calls != 1 {
		t.Fatalf("gateway called for missing snapshot: %d", gateway.calls)
	}
}

func TestPrepareValidatesWorkspaceAndSafeStorageIdentity(t *testing.T) {
	gateway := &fakeCatalogGateway{}
	service := NewService(fakeWorkspaces{err: errors.New("workspace_not_found")}, fakeConnections{}, gateway, t.TempDir())
	if _, err := service.Prepare(context.Background(), "missing"); errorCode(err) != "catalog_workspace_failed" {
		t.Fatalf("workspace error = %v", err)
	}
	service = NewService(fakeWorkspaces{summary: workspace.Summary{ID: "../escape"}}, fakeConnections{}, gateway, t.TempDir())
	if _, err := service.Prepare(context.Background(), "../escape"); errorCode(err) != "catalog_workspace_invalid" {
		t.Fatalf("unsafe id error = %v", err)
	}
}

func TestPrepareRejectsAWorkerResultForAnotherCatalog(t *testing.T) {
	gateway := &fakeCatalogGateway{result: BuildResult{DatabasePath: "/wrong/catalog.duckdb", Fingerprint: "wrong", TableCount: 99}}
	service := NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}}, fakeConnections{}, gateway, t.TempDir())
	if _, err := service.Prepare(context.Background(), "workspace-1"); errorCode(err) != "catalog_invalid_result" {
		t.Fatalf("invalid result error = %v", err)
	}
}

func TestPrepareAcceptsWorkerCanonicalPathForTheRequestedCatalog(t *testing.T) {
	realRoot := t.TempDir()
	aliasParent := t.TempDir()
	aliasRoot := filepath.Join(aliasParent, "catalogs")
	if err := os.Symlink(realRoot, aliasRoot); err != nil {
		t.Skipf("filesystem does not support symlinks: %v", err)
	}
	requested := filepath.Join(aliasRoot, "workspace-1", "workspace.duckdb")
	if err := os.MkdirAll(filepath.Dir(requested), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(requested, []byte("catalog"), 0o600); err != nil {
		t.Fatal(err)
	}
	canonical, err := filepath.EvalSymlinks(requested)
	if err != nil {
		t.Fatal(err)
	}
	gateway := &fakeCatalogGateway{result: BuildResult{DatabasePath: canonical}}
	service := NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}}, fakeConnections{}, gateway, aliasRoot)
	result, err := service.Prepare(context.Background(), "workspace-1")
	if err != nil {
		t.Fatalf("canonical worker path was rejected: %v", err)
	}
	if result.DatabasePath != requested {
		t.Fatalf("public catalog path = %q, want requested path %q", result.DatabasePath, requested)
	}
}

func TestPrepareSerializesBuildsForTheSameWorkspace(t *testing.T) {
	started := make(chan struct{}, 2)
	continueRun := make(chan struct{}, 2)
	gateway := &fakeCatalogGateway{started: started, continueRun: continueRun}
	service := NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1"}}, fakeConnections{}, gateway, t.TempDir())
	results := make(chan error, 2)
	go func() { _, err := service.Prepare(context.Background(), "workspace-1"); results <- err }()
	<-started
	go func() { _, err := service.Prepare(context.Background(), "workspace-1"); results <- err }()
	select {
	case <-started:
		t.Fatal("second catalog build started before the first finished")
	default:
	}
	continueRun <- struct{}{}
	if err := <-results; err != nil {
		t.Fatal(err)
	}
	<-started
	continueRun <- struct{}{}
	if err := <-results; err != nil {
		t.Fatal(err)
	}
}

func TestNativeDatasetAndSchemaContractsHideSnapshotPointersAndPersistOverrides(t *testing.T) {
	connections := connection.ListResponse{Connections: []connection.Connection{{
		ID: "connection-1", WorkspaceID: "workspace-1", Name: "Sales", AdapterKind: connection.AdapterCSV,
		SourcePath: "/user/sales.csv", Status: connection.StatusReady, CreatedAt: "created", UpdatedAt: "updated",
		Outputs: []connection.Output{{SourceObjectID: "file", Name: "sales", SnapshotPath: snapshot(t, "sales"), RowCount: 3, Columns: []connection.Column{{Name: "region", DataType: "VARCHAR", Nullable: true}, {Name: "amount", DataType: "DOUBLE"}}}},
	}}}
	repository := &fakeSchemaRepository{}
	service := NewService(fakeWorkspaces{summary: workspace.Summary{ID: "workspace-1", SchemaContext: "Business context"}}, fakeConnections{response: connections}, &fakeCatalogGateway{}, t.TempDir()).WithSchemaRepository(repository)

	listed, err := service.ListDatasets(context.Background(), "workspace-1")
	if err != nil || len(listed.Datasets) != 1 {
		t.Fatalf("ListDatasets() = %#v, %v", listed, err)
	}
	dataset := listed.Datasets[0]
	if dataset.TableName != "sales" || dataset.SourcePath != "/user/sales.csv" || dataset.FileType != "csv" || dataset.RowCount != 3 {
		t.Fatalf("dataset = %#v", dataset)
	}
	encoded := fmt.Sprintf("%#v", dataset)
	if strings.Contains(encoded, "snapshots") || strings.Contains(encoded, ".parquet") {
		t.Fatalf("dataset leaked snapshot path: %s", encoded)
	}
	summary, err := service.SummarizeWorkspace(context.Background(), "workspace-1")
	if err != nil || summary.TableCount != 1 || len(summary.TableNames) != 1 || summary.TableNames[0] != "sales" {
		t.Fatalf("SummarizeWorkspace() = %#v, %v", summary, err)
	}

	tableContext := "  One row per booked sale.  "
	saved, err := service.SaveSchema(context.Background(), SaveSchemaRequest{WorkspaceID: "workspace-1", TableName: "sales", TableContext: &tableContext, Columns: []SchemaColumn{{Name: "region", Description: "Sales territory", Aliases: []string{"area"}}, {Name: "amount", Description: "Booked revenue"}}})
	if err != nil || saved.Context != "Business context" || saved.TableContext != "One row per booked sale." || saved.Columns[0].DataType != "VARCHAR" || saved.Columns[0].Description != "Sales territory" || len(saved.Columns[0].Aliases) != 1 {
		t.Fatalf("SaveSchema() = %#v, %v", saved, err)
	}
	loaded, err := service.GetSchema(context.Background(), "workspace-1", "sales")
	if err != nil || loaded.Columns[1].Description != "Booked revenue" {
		t.Fatalf("GetSchema() = %#v, %v", loaded, err)
	}
	loaded.Columns[1].Description = "Recognized revenue"
	preserved, err := service.SaveSchema(context.Background(), SaveSchemaRequest{WorkspaceID: "workspace-1", TableName: "sales", Columns: loaded.Columns})
	if err != nil || preserved.TableContext != "One row per booked sale." || preserved.Columns[1].Description != "Recognized revenue" {
		t.Fatalf("column-only SaveSchema() = %#v, %v", preserved, err)
	}
	if _, err := service.SaveSchema(context.Background(), SaveSchemaRequest{WorkspaceID: "workspace-1", TableName: "sales", Columns: []SchemaColumn{{Name: "unknown"}}}); errorCode(err) != "schema_columns_invalid" {
		t.Fatalf("unknown column error = %v", err)
	}
	tooLong := strings.Repeat("x", 8001)
	if _, err := service.SaveSchema(context.Background(), SaveSchemaRequest{WorkspaceID: "workspace-1", TableName: "sales", TableContext: &tooLong, Columns: preserved.Columns}); errorCode(err) != "table_context_invalid" {
		t.Fatalf("long table context error = %v", err)
	}
}
