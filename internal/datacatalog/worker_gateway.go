package datacatalog

import (
	"context"

	"inquira-go/internal/connection"
)

type WorkerGateway struct{ transport connection.RPCTransport }

func NewWorkerGateway(transport connection.RPCTransport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}

func (g *WorkerGateway) Build(ctx context.Context, request BuildRequest) (BuildResult, error) {
	var result BuildResult
	err := g.transport.Call(ctx, "build_catalog", request, &result)
	return result, err
}
