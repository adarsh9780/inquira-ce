package datacatalog

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"sync"
	"testing"

	"inquira-go/internal/apperror"
	"inquira-go/internal/connection"
	"inquira-go/internal/workspace"
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

func (f *fakeCatalogGateway) Build(_ context.Context, request BuildRequest) (BuildResult, error) {
	f.mu.Lock()
	f.calls++
	f.request = request
	started, continueRun := f.started, f.continueRun
	result, err := f.result, f.err
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
