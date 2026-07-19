package analysisagent

import (
	"context"
	"encoding/json"
	"testing"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/worker"
)

type fakeTransport struct {
	method  string
	request AgentWorkerRequest
}

func (f *fakeTransport) CallWithEvents(_ context.Context, method string, params, result any, emit func(worker.Event)) error {
	f.method = method
	f.request = params.(AgentWorkerRequest)
	*(result.(*AgentWorkerResult)) = AgentWorkerResult{Success: true, Answer: "answer"}
	emit(worker.Event{Type: "agent_status", Data: json.RawMessage(`{"stage":"executing"}`)})
	return nil
}

func TestWorkerGatewayUsesAgentRPCAndForwardsStructuredEvents(t *testing.T) {
	transport := &fakeTransport{}
	gateway := NewWorkerGateway(transport)
	events := make([]analysisruntime.WorkerEvent, 0)
	result, err := gateway.Analyze(context.Background(), AgentWorkerRequest{Question: "question"}, func(event analysisruntime.WorkerEvent) {
		events = append(events, event)
	})
	if err != nil || !result.Success || result.Answer != "answer" {
		t.Fatalf("result = %#v, error = %v", result, err)
	}
	if transport.method != "agent_analyze" || transport.request.Question != "question" {
		t.Fatalf("transport method=%q request=%#v", transport.method, transport.request)
	}
	if len(events) != 1 || events[0].Type != "agent_status" {
		t.Fatalf("events = %#v", events)
	}
	data, ok := events[0].Data.(map[string]any)
	if !ok || data["stage"] != "executing" {
		t.Fatalf("event data = %#v", events[0].Data)
	}
}
