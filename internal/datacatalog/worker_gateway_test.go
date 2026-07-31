package datacatalog

import (
	"context"
	"testing"
)

type fakePreviewTransport struct {
	method string
	params any
}

func (f *fakePreviewTransport) Call(_ context.Context, method string, params, result any) error {
	f.method, f.params = method, params
	switch target := result.(type) {
	case *BuildResult:
		*target = BuildResult{TableCount: 1}
	case *DatasetPreview:
		*target = DatasetPreview{TableName: "sales", Mode: DatasetPreviewTail, Limit: 100}
	}
	return nil
}

func TestWorkerGatewayUsesBoundedCatalogPreviewRPCContract(t *testing.T) {
	transport := &fakePreviewTransport{}
	request := WorkerPreviewRequest{
		DatabasePath: "/safe/workspace.duckdb", TableName: "sales", Mode: DatasetPreviewTail, Limit: 100,
	}
	result, err := NewWorkerGateway(transport).Preview(context.Background(), request)
	if err != nil || transport.method != "preview_catalog" || result.Mode != DatasetPreviewTail {
		t.Fatalf("Preview() = %#v, %v method=%q", result, err, transport.method)
	}
	if transport.params != request {
		t.Fatalf("preview params = %#v", transport.params)
	}
}
