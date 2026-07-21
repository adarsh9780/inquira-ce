package artifactbrowser

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
)

type fakeStore struct {
	artifacts []conversation.Artifact
	path      string
	deleted   string
}

func (f *fakeStore) GetArtifact(_ context.Context, id string) (conversation.Artifact, error) {
	for _, artifact := range f.artifacts {
		if artifact.ID == id {
			return artifact, nil
		}
	}
	return conversation.Artifact{}, errors.New("not found")
}
func (f *fakeStore) ListArtifacts(context.Context, string) ([]conversation.Artifact, error) {
	return f.artifacts, nil
}
func (f *fakeStore) ListWorkspaceArtifacts(context.Context, string) ([]conversation.Artifact, error) {
	return f.artifacts, nil
}
func (f *fakeStore) ArtifactPath(context.Context, string) (string, error) { return f.path, nil }
func (f *fakeStore) DeleteArtifact(_ context.Context, id string) error    { f.deleted = id; return nil }

type fakeGateway struct {
	inspected InspectResult
	rows      RowsResult
	path      string
	request   RowsRequest
}

func (f *fakeGateway) Inspect(_ context.Context, path string) (InspectResult, error) {
	f.path = path
	return f.inspected, nil
}
func (f *fakeGateway) Rows(_ context.Context, path string, request RowsRequest) (RowsResult, error) {
	f.path = path
	f.request = request
	return f.rows, nil
}

func TestArtifactBrowserListsMetadataWithoutExposingHeapPaths(t *testing.T) {
	path := filepath.Join(t.TempDir(), "table.parquet")
	if err := os.WriteFile(path, []byte("parquet"), 0o600); err != nil {
		t.Fatal(err)
	}
	artifact := conversation.Artifact{ID: "a1", WorkspaceID: "w1", ConversationID: "c1", TurnID: "t1", Kind: "dataframe", LogicalName: "sales", DisplayName: "Sales", PayloadFormat: "parquet", ByteSize: 7, Status: conversation.ArtifactStatusActive}
	store := &fakeStore{artifacts: []conversation.Artifact{artifact}, path: path}
	gateway := &fakeGateway{inspected: InspectResult{RowCount: 42, Schema: []Column{{Name: "region", Type: "VARCHAR"}}}}
	service := NewService(store, gateway)
	listed, err := service.ListTurn(context.Background(), "c1", "t1", "dataframe")
	if err != nil || listed.Total != 1 || listed.Artifacts[0].RowCount != 42 {
		t.Fatalf("ListTurn()=%#v,%v", listed, err)
	}
	metadata, err := service.MetadataForTurn(context.Background(), "c1", "t1", "a1")
	if err != nil || metadata.Pointer != "artifact://a1" || metadata.RowCount != 42 {
		t.Fatalf("MetadataForTurn()=%#v,%v", metadata, err)
	}
	encoded, _ := json.Marshal(metadata)
	if string(encoded) == "" || containsPath(string(encoded), path) {
		t.Fatalf("metadata leaked path: %s", encoded)
	}
}

func TestArtifactBrowserReadsFigurePayloadPagesRowsAndChecksOwnership(t *testing.T) {
	path := filepath.Join(t.TempDir(), "figure.json")
	if err := os.WriteFile(path, []byte(`{"data":[{"type":"bar"}]}`), 0o600); err != nil {
		t.Fatal(err)
	}
	artifact := conversation.Artifact{ID: "a1", WorkspaceID: "w1", ConversationID: "c1", TurnID: "t1", Kind: "figure", LogicalName: "chart", PayloadFormat: "json", Status: conversation.ArtifactStatusActive}
	store := &fakeStore{artifacts: []conversation.Artifact{artifact}, path: path}
	gateway := &fakeGateway{rows: RowsResult{RowCount: 1, Rows: []map[string]any{{"id": float64(1)}}}}
	service := NewService(store, gateway)
	metadata, err := service.MetadataForWorkspace(context.Background(), "w1", "a1")
	if err != nil || metadata.Payload == nil {
		t.Fatalf("MetadataForWorkspace()=%#v,%v", metadata, err)
	}
	if _, err := service.MetadataForWorkspace(context.Background(), "other", "a1"); errorCode(err) != "artifact_not_found" {
		t.Fatalf("ownership error=%v", err)
	}
	store.artifacts[0].Kind = "dataframe"
	store.artifacts[0].PayloadFormat = "parquet"
	rows, err := service.RowsForTurn(context.Background(), "c1", "t1", "a1", RowsRequest{Offset: 0, Limit: 10})
	if err != nil || rows.ArtifactID != "a1" || len(rows.Rows) != 1 {
		t.Fatalf("RowsForTurn()=%#v,%v", rows, err)
	}
	if gateway.request.SortModel == nil || gateway.request.FilterModel == nil {
		t.Fatalf("optional row query models were not normalized: %#v", gateway.request)
	}
	deleted, err := service.DeleteForTurn(context.Background(), "c1", "t1", "a1")
	if err != nil || !deleted.Deleted || store.deleted != "a1" {
		t.Fatalf("DeleteForTurn()=%#v,%v", deleted, err)
	}
}

func containsPath(value, path string) bool {
	return len(path) > 0 && len(value) >= len(path) && stringContains(value, path)
}
func stringContains(value, needle string) bool {
	for i := 0; i+len(needle) <= len(value); i++ {
		if value[i:i+len(needle)] == needle {
			return true
		}
	}
	return false
}
func errorCode(err error) string {
	var target *apperror.Error
	if errors.As(err, &target) {
		return target.Code
	}
	return ""
}
