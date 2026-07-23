package connection

import (
	"context"
	"testing"
)

type fakeRPCTransport struct {
	method string
	params any
	result any
	err    error
}

func (f *fakeRPCTransport) Call(_ context.Context, method string, params, result any) error {
	f.method = method
	f.params = params
	if f.err != nil {
		return f.err
	}
	switch target := result.(type) {
	case *Discovery:
		*target = f.result.(Discovery)
	case *Preview:
		*target = f.result.(Preview)
	case *Materialization:
		*target = f.result.(Materialization)
	}
	return nil
}

func TestWorkerGatewayMapsTheAdapterContractToRPC(t *testing.T) {
	transport := &fakeRPCTransport{result: Discovery{AdapterKind: AdapterCSV, Fingerprint: "hash"}}
	gateway := NewWorkerGateway(transport)
	discovery, err := gateway.Discover(context.Background(), AdapterRequest{AdapterKind: AdapterCSV, SourcePath: "/tmp/data.csv"})
	if err != nil || discovery.Fingerprint != "hash" || transport.method != "discover" {
		t.Fatalf("Discover() = %#v, %v; method = %q", discovery, err, transport.method)
	}

	transport.result = Preview{Rows: []map[string]any{{"id": float64(1)}}}
	if _, err := gateway.Preview(context.Background(), AdapterRequest{AdapterKind: AdapterExcel, SourceObjectID: "sheet:Sales"}, 25); err != nil || transport.method != "preview" {
		t.Fatalf("Preview() error = %v; method = %q", err, transport.method)
	}
	params := transport.params.(map[string]any)
	if params["limit"] != 25 || params["source_object_id"] != "sheet:Sales" {
		t.Fatalf("preview params = %#v", params)
	}

	transport.result = defaultMaterialization("hash")
	if _, err := gateway.Materialize(context.Background(), MaterializeRequest{AdapterKind: AdapterCSV}); err != nil || transport.method != "materialize" {
		t.Fatalf("Materialize() error = %v; method = %q", err, transport.method)
	}
}
