package analysisagent

import (
	"context"
	"encoding/json"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/worker"
)

type runtimeTransport interface {
	Call(context.Context, string, any, any) error
	CallWithEvents(context.Context, string, any, any, func(worker.Event)) error
}

type WorkerGateway struct{ transport runtimeTransport }

func NewWorkerGateway(transport runtimeTransport) *WorkerGateway {
	return &WorkerGateway{transport: transport}
}

func (g *WorkerGateway) Cancel(ctx context.Context, workspaceID, clientRequestID string) (bool, error) {
	var result struct {
		Cancelled bool `json:"cancelled"`
	}
	err := g.transport.Call(ctx, "agent_cancel", map[string]any{
		"workspace_id": workspaceID, "client_request_id": clientRequestID,
	}, &result)
	return result.Cancelled, err
}

func (g *WorkerGateway) Analyze(
	ctx context.Context,
	request AgentWorkerRequest,
	emit func(analysisruntime.WorkerEvent),
) (AgentWorkerResult, error) {
	var result AgentWorkerResult
	err := g.transport.CallWithEvents(ctx, "agent_analyze", request, &result, func(event worker.Event) {
		if emit == nil {
			return
		}
		var data any
		if len(event.Data) > 0 && json.Unmarshal(event.Data, &data) != nil {
			data = nil
		}
		emit(analysisruntime.WorkerEvent{Type: event.Type, Data: data})
	})
	return result, err
}
