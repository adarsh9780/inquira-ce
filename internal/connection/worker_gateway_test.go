package connection

import (
	"context"
	"errors"
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

type fakeProcessRunner struct {
	stdout []byte
	stderr []byte
	err    error
	input  []byte
	calls  int
}

func (f *fakeProcessRunner) Run(_ context.Context, executable string, arguments, environment []string, input []byte) ([]byte, []byte, error) {
	f.calls++
	f.input = append([]byte(nil), input...)
	return f.stdout, f.stderr, f.err
}

func TestSubprocessTransportRejectsAStaleRuntimeBeforeStartingPython(t *testing.T) {
	runner := &fakeProcessRunner{stdout: []byte(`{"id":"request","result":{},"error":null}`)}
	transport := NewSubprocessTransport("/python", "/worker/src", runner).WithReadinessCheck(func() bool { return false })
	if err := transport.Call(context.Background(), "discover", map[string]any{}, &struct{}{}); rpcErrorCode(err) != "runtime_not_ready" {
		t.Fatalf("stale runtime error = %v", err)
	}
	if runner.calls != 0 {
		t.Fatalf("stale runtime started Python %d times", runner.calls)
	}
}

func TestSubprocessTransportDecodesSuccessAndStructuredErrors(t *testing.T) {
	runner := &fakeProcessRunner{stdout: []byte(`{"id":"request","result":{"fingerprint":"hash"},"error":null}`)}
	transport := NewSubprocessTransport("/runtime/python", "/runtime/worker/src", runner)
	var result struct {
		Fingerprint string `json:"fingerprint"`
	}
	if err := transport.Call(context.Background(), "discover", map[string]any{"adapter_kind": "csv"}, &result); err != nil {
		t.Fatal(err)
	}
	if result.Fingerprint != "hash" || len(runner.input) == 0 {
		t.Fatalf("result = %#v input = %q", result, runner.input)
	}

	runner.stdout = []byte(`{"id":"request","result":null,"error":{"code":"source_unreadable","message":"bad file"}}`)
	if err := transport.Call(context.Background(), "discover", map[string]any{}, &result); rpcErrorCode(err) != "source_unreadable" {
		t.Fatalf("structured error = %v", err)
	}
}

func TestSubprocessTransportRejectsMissingRuntimeProcessFailuresAndMalformedResponses(t *testing.T) {
	runner := &fakeProcessRunner{}
	transport := NewSubprocessTransport("", "/worker/src", runner)
	if err := transport.Call(context.Background(), "discover", nil, &struct{}{}); rpcErrorCode(err) != "runtime_not_ready" {
		t.Fatalf("missing runtime error = %v", err)
	}

	transport = NewSubprocessTransport("/python", "/worker/src", runner)
	runner.err = errors.New("exit status 1")
	runner.stderr = []byte("private internal traceback")
	if err := transport.Call(context.Background(), "discover", nil, &struct{}{}); rpcErrorCode(err) != "worker_process_failed" {
		t.Fatalf("process error = %v", err)
	}
	runner.err = nil
	runner.stdout = []byte("not json")
	if err := transport.Call(context.Background(), "discover", nil, &struct{}{}); rpcErrorCode(err) != "worker_invalid_response" {
		t.Fatalf("decode error = %v", err)
	}
}

func rpcErrorCode(err error) string {
	var rpcError *RPCError
	if errors.As(err, &rpcError) {
		return rpcError.Code
	}
	return ""
}
