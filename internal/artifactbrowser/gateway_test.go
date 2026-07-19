package artifactbrowser

import (
	"context"
	"testing"
)

type fakeTransport struct {
	method string
	params map[string]any
}

func (f *fakeTransport) Call(_ context.Context, method string, params, result any) error {
	f.method = method
	f.params = params.(map[string]any)
	switch target := result.(type) {
	case *InspectResult:
		*target = InspectResult{RowCount: 3}
	case *RowsResult:
		*target = RowsResult{RowCount: 1}
	}
	return nil
}

func TestWorkerGatewayUsesArtifactRPCContract(t *testing.T) {
	transport := &fakeTransport{}
	gateway := NewWorkerGateway(transport)
	if result, err := gateway.Inspect(context.Background(), "/safe/data.parquet"); err != nil || result.RowCount != 3 || transport.method != "artifact_inspect" {
		t.Fatalf("Inspect() = %#v, %v; method = %q", result, err, transport.method)
	}
	request := RowsRequest{Offset: 2, Limit: 5, SearchText: "north"}
	if _, err := gateway.Rows(context.Background(), "/safe/data.parquet", request); err != nil || transport.method != "artifact_rows" {
		t.Fatalf("Rows() error = %v; method = %q", err, transport.method)
	}
	if transport.params["offset"] != 2 || transport.params["limit"] != 5 || transport.params["search_text"] != "north" {
		t.Fatalf("row params = %#v", transport.params)
	}
}
