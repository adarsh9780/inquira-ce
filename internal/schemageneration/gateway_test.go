package schemageneration

import (
	"context"
	"testing"
)

type fakeTransport struct {
	method string
	params any
}

func (f *fakeTransport) Call(_ context.Context, method string, params, result any) error {
	f.method, f.params = method, params
	output := result.(*GenerateResult)
	output.Columns = []GeneratedColumn{{Name: "amount", Description: "Booked revenue"}}
	return nil
}

func TestWorkerGatewayUsesSchemaDescribeRPCContract(t *testing.T) {
	transport := &fakeTransport{}
	result, err := NewWorkerGateway(transport).Generate(context.Background(), GenerateRequest{WorkspaceID: "workspace", TableName: "sales"})
	if err != nil || transport.method != "schema_describe" || len(result.Columns) != 1 {
		t.Fatalf("Generate() = %#v, %v method=%q params=%#v", result, err, transport.method, transport.params)
	}
}
