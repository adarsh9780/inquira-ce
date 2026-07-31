package connection

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/adarsh9780/inquira-ce/internal/apperror"
	"github.com/adarsh9780/inquira-ce/internal/workspace"
)

type fakeGateway struct {
	mu                  sync.Mutex
	discovery           Discovery
	preview             Preview
	materialization     Materialization
	discoverErr         error
	discoverCalls       int
	previewErr          error
	previewRequest      AdapterRequest
	materializeErr      error
	materializeCalls    int
	materializeStarted  chan struct{}
	materializeContinue chan struct{}
}

func (f *fakeGateway) Discover(_ context.Context, request AdapterRequest) (Discovery, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.discoverCalls++
	result := f.discovery
	if result.Objects == nil && (request.AdapterKind == AdapterCSV || request.AdapterKind == AdapterParquet || request.AdapterKind == AdapterJSON) {
		result.Objects = []SourceObject{{ID: "file", Name: "file", Kind: "table"}}
	}
	return result, f.discoverErr
}

func (f *fakeGateway) Preview(_ context.Context, request AdapterRequest, _ int) (Preview, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.previewRequest = request
	return f.preview, f.previewErr
}

func (f *fakeGateway) Materialize(_ context.Context, request MaterializeRequest) (Materialization, error) {
	f.mu.Lock()
	f.materializeCalls++
	started := f.materializeStarted
	continued := f.materializeContinue
	result := f.materialization
	err := f.materializeErr
	f.mu.Unlock()
	if started != nil {
		select {
		case started <- struct{}{}:
		default:
		}
	}
	if continued != nil {
		<-continued
	}
	if err != nil {
		return Materialization{}, err
	}
	for _, output := range result.Outputs {
		path := filepath.Join(request.TargetDir, filepath.FromSlash(output.RelativePath))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			return Materialization{}, err
		}
		if err := os.WriteFile(path, []byte("snapshot"), 0o600); err != nil {
			return Materialization{}, err
		}
	}
	return result, nil
}

func defaultMaterialization(fingerprint string) Materialization {
	return Materialization{
		Fingerprint: fingerprint,
		Outputs: []MaterializedOutput{{
			SourceObjectID: "file", Name: "sales", RelativePath: "data.parquet",
			Format: "parquet", Columns: []Column{{Name: "id", DataType: "BIGINT", Nullable: true}},
			RowCount: 2, ByteSize: 8,
		}},
	}
}

func newTestService(t *testing.T, gateway *fakeGateway) (*Service, string, string) {
	t.Helper()
	root := t.TempDir()
	databasePath := filepath.Join(root, "data", "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	workspaceService := workspace.NewService(workspaceRepository)
	createdWorkspace, err := workspaceService.Create(context.Background(), workspace.CreateRequest{Name: "Analytics"})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = workspaceService.Close() })
	repository, err := OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = repository.Close() })
	return NewService(repository, gateway, filepath.Join(root, "snapshots")), createdWorkspace.ID, databasePath
}

func createSource(t *testing.T, suffix string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "source"+suffix)
	if err := os.WriteFile(path, []byte("id\n1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestCreatePersistsAReadyConnectionAndPublishedSnapshot(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("sha256:first")}
	service, workspaceID, databasePath := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: " Sales file ", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".CSV"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	if created.Name != "Sales file" || created.Status != StatusReady || created.SourceFingerprint != "sha256:first" {
		t.Fatalf("created = %#v", created)
	}
	if len(created.Outputs) != 1 || created.Outputs[0].RowCount != 2 {
		t.Fatalf("outputs = %#v", created.Outputs)
	}
	if !filepath.IsAbs(created.Outputs[0].SnapshotPath) {
		t.Fatalf("snapshot path should be absolute: %q", created.Outputs[0].SnapshotPath)
	}
	if _, err := os.Stat(created.Outputs[0].SnapshotPath); err != nil {
		t.Fatalf("published snapshot missing: %v", err)
	}
	listed, err := service.List(context.Background(), workspaceID)
	if err != nil || len(listed.Connections) != 1 || len(listed.Connections[0].Outputs) != 1 {
		t.Fatalf("List() = %#v, %v", listed, err)
	}

	reopened, err := OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	persisted, err := reopened.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if persisted.ID != created.ID || persisted.Outputs[0].SnapshotPath != created.Outputs[0].SnapshotPath {
		t.Fatalf("persisted = %#v", persisted)
	}
}

func TestCreateValidatesWorkspaceNameKindSourceAndSelection(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("fingerprint")}
	service, workspaceID, _ := newTestService(t, gateway)
	csvPath := createSource(t, ".csv")
	tests := []struct {
		name    string
		request CreateRequest
		code    string
	}{
		{"missing workspace", CreateRequest{Name: "Data", AdapterKind: AdapterCSV, SourcePath: csvPath, SelectedObjectIDs: []string{"file"}}, "workspace_required"},
		{"unknown workspace", CreateRequest{WorkspaceID: "missing", Name: "Data", AdapterKind: AdapterCSV, SourcePath: csvPath, SelectedObjectIDs: []string{"file"}}, "workspace_not_found"},
		{"blank name", CreateRequest{WorkspaceID: workspaceID, Name: " ", AdapterKind: AdapterCSV, SourcePath: csvPath, SelectedObjectIDs: []string{"file"}}, "connection_name_required"},
		{"unsupported kind", CreateRequest{WorkspaceID: workspaceID, Name: "Data", AdapterKind: AdapterKind("postgres"), SourcePath: csvPath, SelectedObjectIDs: []string{"file"}}, "adapter_not_supported"},
		{"missing source", CreateRequest{WorkspaceID: workspaceID, Name: "Data", AdapterKind: AdapterCSV, SourcePath: filepath.Join(t.TempDir(), "missing.csv"), SelectedObjectIDs: []string{"file"}}, "source_not_found"},
		{"directory source", CreateRequest{WorkspaceID: workspaceID, Name: "Data", AdapterKind: AdapterCSV, SourcePath: t.TempDir(), SelectedObjectIDs: []string{"file"}}, "source_not_file"},
		{"wrong extension", CreateRequest{WorkspaceID: workspaceID, Name: "Data", AdapterKind: AdapterParquet, SourcePath: csvPath, SelectedObjectIDs: []string{"file"}}, "source_extension_mismatch"},
		{"no selection", CreateRequest{WorkspaceID: workspaceID, Name: "Data", AdapterKind: AdapterCSV, SourcePath: csvPath}, "source_selection_required"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if _, err := service.Create(context.Background(), test.request); appErrorCode(err) != test.code {
				t.Fatalf("error = %v, want code %q", err, test.code)
			}
		})
	}
}

func TestExcelPreviewPassesTheSelectedSheetToTheAdapter(t *testing.T) {
	gateway := &fakeGateway{preview: Preview{Rows: []map[string]any{{"id": float64(1)}}}}
	service, _, _ := newTestService(t, gateway)
	path := createSource(t, ".xlsx")
	_, err := service.Preview(context.Background(), PreviewRequest{
		AdapterKind: AdapterExcel, SourcePath: path, SourceObjectID: "sheet:Sales", Limit: 25,
	})
	if err != nil {
		t.Fatal(err)
	}
	if gateway.previewRequest.SourceObjectID != "sheet:Sales" {
		t.Fatalf("preview request = %#v", gateway.previewRequest)
	}
}

func TestRefreshMarksExcelConnectionAsNeedingAttentionWhenASelectedSheetDisappears(t *testing.T) {
	gateway := &fakeGateway{
		materialization: Materialization{Fingerprint: "first", Outputs: []MaterializedOutput{
			{SourceObjectID: "sheet:Sales", Name: "Sales", RelativePath: "sales.parquet", Format: "parquet", RowCount: 2},
		}},
		discovery: Discovery{Fingerprint: "changed", Objects: []SourceObject{{ID: "sheet:Renamed", Name: "Renamed", Kind: "sheet"}}},
	}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Workbook", AdapterKind: AdapterExcel,
		SourcePath: createSource(t, ".xlsx"), SelectedObjectIDs: []string{"sheet:Sales"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := service.Refresh(context.Background(), created.ID); appErrorCode(err) != "connection_needs_attention" {
		t.Fatalf("refresh error = %v", err)
	}
	persisted, err := service.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if persisted.Status != StatusNeedsAttention || persisted.Outputs[0].SnapshotPath != created.Outputs[0].SnapshotPath {
		t.Fatalf("persisted = %#v", persisted)
	}
}

func TestConnectionNamesAreUniquePerWorkspaceIgnoringCaseAndWhitespace(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("fingerprint")}
	service, workspaceID, _ := newTestService(t, gateway)
	path := createSource(t, ".csv")
	request := CreateRequest{WorkspaceID: workspaceID, Name: "Quarterly   Sales", AdapterKind: AdapterCSV, SourcePath: path, SelectedObjectIDs: []string{"file"}}
	if _, err := service.Create(context.Background(), request); err != nil {
		t.Fatal(err)
	}
	request.Name = " quarterly sales "
	if _, err := service.Create(context.Background(), request); appErrorCode(err) != "connection_name_exists" {
		t.Fatalf("duplicate error = %v", err)
	}
}

func TestCreateRejectsUnsafeOrInconsistentAdapterOutputsWithoutPublishing(t *testing.T) {
	unsafeOutputs := []MaterializedOutput{
		{SourceObjectID: "file", Name: "bad", RelativePath: "../escape.parquet", Format: "parquet", RowCount: 1},
	}
	gateway := &fakeGateway{materialization: Materialization{Fingerprint: "fingerprint", Outputs: unsafeOutputs}}
	service, workspaceID, _ := newTestService(t, gateway)
	_, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Unsafe", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if appErrorCode(err) != "adapter_invalid_output" {
		t.Fatalf("unsafe output error = %v", err)
	}
	listed, listErr := service.List(context.Background(), workspaceID)
	if listErr != nil || len(listed.Connections) != 0 {
		t.Fatalf("connections = %#v, error = %v", listed.Connections, listErr)
	}
}

func TestCreateRejectsOutputsThatWereNotSelected(t *testing.T) {
	gateway := &fakeGateway{materialization: Materialization{
		Fingerprint: "fingerprint",
		Outputs:     []MaterializedOutput{{SourceObjectID: "unexpected", Name: "bad", RelativePath: "data.parquet", Format: "parquet", RowCount: 1}},
	}}
	service, workspaceID, _ := newTestService(t, gateway)
	_, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Unexpected", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if appErrorCode(err) != "adapter_invalid_output" {
		t.Fatalf("unselected output error = %v", err)
	}
}

func TestConnectionContractPersistsMultipleSelectedOutputs(t *testing.T) {
	gateway := &fakeGateway{materialization: Materialization{
		Fingerprint: "multi",
		Outputs: []MaterializedOutput{
			{SourceObjectID: "sheet:orders", Name: "orders", RelativePath: "orders.parquet", Format: "parquet", RowCount: 4},
			{SourceObjectID: "sheet:customers", Name: "customers", RelativePath: "customers.parquet", Format: "parquet", RowCount: 3},
		},
	}}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Workbook", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"sheet:orders", "sheet:customers"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(created.Outputs) != 2 || created.Outputs[0].ConnectionID != created.ID || created.Outputs[1].ConnectionID != created.ID {
		t.Fatalf("outputs = %#v", created.Outputs)
	}
	persisted, err := service.Get(context.Background(), created.ID)
	if err != nil || len(persisted.Outputs) != 2 {
		t.Fatalf("persisted = %#v, %v", persisted, err)
	}
}

func TestRefreshAtomicallyReplacesChangedSnapshotAndRemovesTheOldOne(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("first"), discovery: Discovery{Fingerprint: "second"}}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	oldPath := created.Outputs[0].SnapshotPath
	gateway.materialization = defaultMaterialization("second")
	refreshed, err := service.Refresh(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("Refresh() error = %v", err)
	}
	if refreshed.SourceFingerprint != "second" || refreshed.Outputs[0].SnapshotPath == oldPath {
		t.Fatalf("refreshed = %#v", refreshed)
	}
	if _, err := os.Stat(refreshed.Outputs[0].SnapshotPath); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(oldPath); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("old snapshot should be removed, stat error = %v", err)
	}
}

func TestRefreshSkipsMaterializationWhenTheSourceFingerprintIsUnchanged(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("same"), discovery: Discovery{Fingerprint: "same"}}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	refreshed, err := service.Refresh(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if refreshed.Outputs[0].SnapshotPath != created.Outputs[0].SnapshotPath || gateway.materializeCalls != 1 {
		t.Fatalf("unchanged refresh materialized again: calls=%d", gateway.materializeCalls)
	}
}

func TestRefreshWorkspaceReportsSuccessesAndSafeFailures(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("first"), discovery: Discovery{Fingerprint: "changed"}}
	service, workspaceID, _ := newTestService(t, gateway)
	for _, name := range []string{"Sales", "Customers"} {
		if _, err := service.Create(context.Background(), CreateRequest{
			WorkspaceID: workspaceID, Name: name, AdapterKind: AdapterCSV,
			SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
		}); err != nil {
			t.Fatal(err)
		}
	}
	gateway.materialization = defaultMaterialization("changed")

	refreshed, err := service.RefreshWorkspace(context.Background(), workspaceID)
	if err != nil || refreshed.Attempted != 2 || refreshed.Succeeded != 2 || refreshed.Changed != 2 || len(refreshed.Failures) != 0 {
		t.Fatalf("RefreshWorkspace() = %#v, %v", refreshed, err)
	}

	gateway.discoverErr = errors.New("private source path and credential detail")
	failed, err := service.RefreshWorkspace(context.Background(), workspaceID)
	if err != nil || failed.Attempted != 2 || failed.Succeeded != 0 || failed.Changed != 0 || len(failed.Failures) != 2 {
		t.Fatalf("failed RefreshWorkspace() = %#v, %v", failed, err)
	}
	if gateway.discoverCalls != 4 || strings.Contains(failed.Failures[0].Message, "credential") {
		t.Fatalf("workspace refresh did not continue safely: calls=%d failures=%#v", gateway.discoverCalls, failed.Failures)
	}
}

func TestFailedRefreshKeepsLastGoodSnapshotAndRecordsTheError(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("first"), discovery: Discovery{Fingerprint: "changed"}}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	gateway.materializeErr = errors.New("source became unreadable")
	if _, err := service.Refresh(context.Background(), created.ID); appErrorCode(err) != "connection_refresh_failed" {
		t.Fatalf("refresh error = %v", err)
	}
	persisted, err := service.Get(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if persisted.Status != StatusError || persisted.ErrorMessage == "" || persisted.Outputs[0].SnapshotPath != created.Outputs[0].SnapshotPath {
		t.Fatalf("persisted after failure = %#v", persisted)
	}
	if _, err := os.Stat(created.Outputs[0].SnapshotPath); err != nil {
		t.Fatalf("last good snapshot missing: %v", err)
	}
}

func TestConcurrentRefreshesForOneConnectionAreSerialized(t *testing.T) {
	started := make(chan struct{}, 2)
	continued := make(chan struct{}, 2)
	gateway := &fakeGateway{
		materialization: defaultMaterialization("first"), discovery: Discovery{Fingerprint: "changed"},
	}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	gateway.materialization = defaultMaterialization("changed")
	gateway.materializeStarted = started
	gateway.materializeContinue = continued
	results := make(chan error, 2)
	go func() { _, err := service.Refresh(context.Background(), created.ID); results <- err }()
	<-started
	go func() { _, err := service.Refresh(context.Background(), created.ID); results <- err }()
	select {
	case <-started:
		t.Fatal("second refresh entered materialization before the first completed")
	case <-time.After(75 * time.Millisecond):
	}
	continued <- struct{}{}
	if err := <-results; err != nil {
		t.Fatal(err)
	}
	if err := <-results; err != nil {
		t.Fatal(err)
	}
}

func TestDeleteRemovesMetadataAndAllConnectionSnapshots(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("first")}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	root := filepath.Dir(filepath.Dir(created.Outputs[0].SnapshotPath))
	if err := service.Delete(context.Background(), created.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := service.Get(context.Background(), created.ID); appErrorCode(err) != "connection_not_found" {
		t.Fatalf("Get after delete error = %v", err)
	}
	if _, err := os.Stat(root); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("connection snapshot root still exists: %v", err)
	}
}

func TestDeletingAWorkspaceCascadesConnectionMetadata(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("first")}
	service, workspaceID, databasePath := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	workspaceRepository, err := workspace.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	workspaceService := workspace.NewService(workspaceRepository)
	if _, err := workspaceService.Delete(context.Background(), workspaceID); err != nil {
		t.Fatal(err)
	}
	_ = workspaceService.Close()
	if _, err := service.Get(context.Background(), created.ID); appErrorCode(err) != "connection_not_found" {
		t.Fatalf("connection should cascade with workspace, error = %v", err)
	}
}

func TestDeleteWorkspaceConnectionsRemovesSnapshotsBeforeWorkspaceDeletion(t *testing.T) {
	gateway := &fakeGateway{materialization: defaultMaterialization("first")}
	service, workspaceID, _ := newTestService(t, gateway)
	created, err := service.Create(context.Background(), CreateRequest{
		WorkspaceID: workspaceID, Name: "Sales", AdapterKind: AdapterCSV,
		SourcePath: createSource(t, ".csv"), SelectedObjectIDs: []string{"file"},
	})
	if err != nil {
		t.Fatal(err)
	}
	connectionRoot := filepath.Dir(filepath.Dir(filepath.Dir(created.Outputs[0].SnapshotPath)))
	if err := service.DeleteWorkspaceConnections(context.Background(), workspaceID); err != nil {
		t.Fatal(err)
	}
	listed, err := service.List(context.Background(), workspaceID)
	if err != nil || len(listed.Connections) != 0 {
		t.Fatalf("connections = %#v, error = %v", listed.Connections, err)
	}
	if _, err := os.Stat(connectionRoot); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("connection root remains after workspace cleanup: %v", err)
	}
}

func appErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
