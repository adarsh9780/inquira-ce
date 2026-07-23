package connection

import (
	"context"
)

type RPCTransport interface {
	Call(context.Context, string, any, any) error
}

type WorkerGateway struct {
	transport RPCTransport
}

func NewWorkerGateway(transport RPCTransport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}

func (g *WorkerGateway) Discover(ctx context.Context, request AdapterRequest) (Discovery, error) {
	var result Discovery
	err := g.transport.Call(ctx, "discover", adapterParams(request), &result)
	return result, err
}

func (g *WorkerGateway) Preview(ctx context.Context, request AdapterRequest, limit int) (Preview, error) {
	params := adapterParams(request)
	params["limit"] = limit
	var result Preview
	err := g.transport.Call(ctx, "preview", params, &result)
	return result, err
}

func (g *WorkerGateway) Materialize(ctx context.Context, request MaterializeRequest) (Materialization, error) {
	params := map[string]any{
		"adapter_kind":        request.AdapterKind,
		"source_path":         request.SourcePath,
		"target_dir":          request.TargetDir,
		"selected_object_ids": request.SelectedObjectIDs,
		"options":             request.Options,
	}
	var result Materialization
	err := g.transport.Call(ctx, "materialize", params, &result)
	return result, err
}

func adapterParams(request AdapterRequest) map[string]any {
	return map[string]any{
		"adapter_kind":     request.AdapterKind,
		"source_path":      request.SourcePath,
		"source_object_id": request.SourceObjectID,
		"options":          request.Options,
	}
}
