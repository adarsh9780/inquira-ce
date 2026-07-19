package schemageneration

import "context"

type rpcTransport interface {
	Call(context.Context, string, any, any) error
}

type WorkerGateway struct{ transport rpcTransport }

func NewWorkerGateway(transport rpcTransport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}

func (g *WorkerGateway) Generate(ctx context.Context, request GenerateRequest) (GenerateResult, error) {
	var result GenerateResult
	err := g.transport.Call(ctx, "schema_describe", request, &result)
	return result, err
}
