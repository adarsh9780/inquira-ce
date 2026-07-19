package artifactbrowser

import "context"

type transport interface {
	Call(context.Context, string, any, any) error
}
type WorkerGateway struct{ transport transport }

func NewWorkerGateway(transport transport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}
func (g *WorkerGateway) Inspect(ctx context.Context, path string) (InspectResult, error) {
	var result InspectResult
	err := g.transport.Call(ctx, "artifact_inspect", map[string]any{"artifact_path": path}, &result)
	return result, err
}
func (g *WorkerGateway) Rows(ctx context.Context, path string, request RowsRequest) (RowsResult, error) {
	var result RowsResult
	err := g.transport.Call(ctx, "artifact_rows", map[string]any{"artifact_path": path, "offset": request.Offset, "limit": request.Limit, "sort_model": request.SortModel, "filter_model": request.FilterModel, "search_text": request.SearchText}, &result)
	return result, err
}
