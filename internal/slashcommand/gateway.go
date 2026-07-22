package slashcommand

import "context"

type compileTransport interface {
	Call(context.Context, string, any, any) error
}

type WorkerGateway struct {
	transport compileTransport
}

func NewWorkerGateway(transport compileTransport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}

func (g *WorkerGateway) Compile(ctx context.Context, request CompileRequest) (CompiledCommand, error) {
	var result CompiledCommand
	err := g.transport.Call(ctx, "command_compile", request, &result)
	return result, err
}

func (g *WorkerGateway) List(ctx context.Context) (Catalog, error) {
	var result Catalog
	err := g.transport.Call(ctx, "command_list", map[string]any{}, &result)
	return result, err
}
