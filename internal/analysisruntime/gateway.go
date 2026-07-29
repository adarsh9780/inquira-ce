package analysisruntime

import (
	"context"
	"encoding/json"

	"github.com/adarsh9780/inquira-ce/internal/worker"
)

type runtimeTransport interface {
	Call(context.Context, string, any, any) error
	CallWithEvents(context.Context, string, any, any, func(worker.Event)) error
}

type WorkerGateway struct {
	transport runtimeTransport
}

func NewWorkerGateway(transport runtimeTransport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}

func (g *WorkerGateway) Execute(ctx context.Context, request ExecuteWorkerRequest, emit func(WorkerEvent)) (ExecuteWorkerResult, error) {
	var result ExecuteWorkerResult
	err := g.transport.CallWithEvents(ctx, "kernel_execute", request, &result, func(event worker.Event) {
		if emit == nil {
			return
		}
		var data any
		if len(event.Data) > 0 {
			if unmarshalErr := json.Unmarshal(event.Data, &data); unmarshalErr != nil {
				data = nil
			}
		}
		emit(WorkerEvent{Type: event.Type, Data: data})
	})
	return result, err
}

func (g *WorkerGateway) Status(ctx context.Context, workspaceID string) (KernelStatus, error) {
	var result KernelStatus
	err := g.transport.Call(ctx, "kernel_status", map[string]any{"workspace_id": workspaceID}, &result)
	return result, err
}

func (g *WorkerGateway) Reset(ctx context.Context, workspaceID string) (bool, error) {
	var result struct {
		Reset bool `json:"reset"`
	}
	err := g.transport.Call(ctx, "kernel_reset", map[string]any{"workspace_id": workspaceID}, &result)
	return result.Reset, err
}

func (g *WorkerGateway) Interrupt(ctx context.Context, workspaceID string) (bool, error) {
	var result struct {
		Interrupted bool `json:"interrupted"`
	}
	err := g.transport.Call(ctx, "kernel_interrupt", map[string]any{"workspace_id": workspaceID}, &result)
	return result.Interrupted, err
}
