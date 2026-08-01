package datacatalog

import (
	"context"

	"github.com/adarsh9780/inquira-ce/internal/connection"
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

func (g *WorkerGateway) Preview(ctx context.Context, request WorkerPreviewRequest) (DatasetPreview, error) {
	var result DatasetPreview
	err := g.transport.Call(ctx, "preview_catalog", request, &result)
	return result, err
}
