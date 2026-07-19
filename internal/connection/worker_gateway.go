package connection

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"
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

type RPCError struct {
	Code    string
	Message string
	Cause   error
}

func (e *RPCError) Error() string {
	if e == nil {
		return ""
	}
	if e.Message == "" {
		return e.Code
	}
	return e.Message
}

func (e *RPCError) Unwrap() error { return e.Cause }

type processRunner interface {
	Run(context.Context, string, []string, []string, []byte) ([]byte, []byte, error)
}

type execProcessRunner struct{}

func (execProcessRunner) Run(ctx context.Context, executable string, arguments, environment []string, input []byte) ([]byte, []byte, error) {
	command := exec.CommandContext(ctx, executable, arguments...)
	command.Env = append(os.Environ(), environment...)
	command.Stdin = bytes.NewReader(input)
	var stdout, stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	err := command.Run()
	return stdout.Bytes(), stderr.Bytes(), err
}

type SubprocessTransport struct {
	pythonExecutable string
	workerSourceDir  string
	runner           processRunner
	readinessCheck   func() bool
}

func (t *SubprocessTransport) WithReadinessCheck(check func() bool) *SubprocessTransport {
	t.readinessCheck = check
	return t
}

func NewSubprocessTransport(pythonExecutable, workerSourceDir string, runner processRunner) *SubprocessTransport {
	if runner == nil {
		runner = execProcessRunner{}
	}
	return &SubprocessTransport{
		pythonExecutable: strings.TrimSpace(pythonExecutable),
		workerSourceDir:  strings.TrimSpace(workerSourceDir),
		runner:           runner,
	}
}

func (t *SubprocessTransport) Call(ctx context.Context, method string, params, result any) error {
	if t.pythonExecutable == "" || t.workerSourceDir == "" {
		return &RPCError{Code: "runtime_not_ready", Message: "Configure the Python data runtime before creating a connection."}
	}
	if t.readinessCheck != nil && !t.readinessCheck() {
		return &RPCError{Code: "runtime_not_ready", Message: "Configure or update the Python data runtime before creating a connection."}
	}
	if _, isDefaultRunner := t.runner.(execProcessRunner); isDefaultRunner {
		if info, err := os.Stat(t.pythonExecutable); err != nil || !info.Mode().IsRegular() {
			return &RPCError{Code: "runtime_not_ready", Message: "Configure the Python data runtime before creating a connection.", Cause: err}
		}
		if info, err := os.Stat(t.workerSourceDir); err != nil || !info.IsDir() {
			return &RPCError{Code: "runtime_not_ready", Message: "The bundled Python data worker is unavailable.", Cause: err}
		}
	}
	request := struct {
		ID     string `json:"id"`
		Method string `json:"method"`
		Params any    `json:"params"`
	}{ID: "request", Method: method, Params: params}
	input, err := json.Marshal(request)
	if err != nil {
		return &RPCError{Code: "worker_request_failed", Message: "Could not encode the data worker request.", Cause: err}
	}
	input = append(input, '\n')
	stdout, _, err := t.runner.Run(ctx, t.pythonExecutable, []string{"-m", "inquira_data_worker"},
		[]string{"PYTHONPATH=" + t.workerSourceDir}, input)
	if err != nil {
		if errors.Is(ctx.Err(), context.Canceled) || errors.Is(ctx.Err(), context.DeadlineExceeded) {
			return &RPCError{Code: "worker_cancelled", Message: "The data worker request was cancelled.", Cause: ctx.Err()}
		}
		return &RPCError{Code: "worker_process_failed", Message: "The Python data worker could not be started or exited unexpectedly.", Cause: err}
	}
	var response struct {
		ID     string          `json:"id"`
		Result json.RawMessage `json:"result"`
		Error  *struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(stdout, &response); err != nil || response.ID != request.ID {
		return &RPCError{Code: "worker_invalid_response", Message: "The Python data worker returned an invalid response.", Cause: err}
	}
	if response.Error != nil {
		return &RPCError{Code: response.Error.Code, Message: response.Error.Message}
	}
	if len(response.Result) == 0 || string(response.Result) == "null" {
		return &RPCError{Code: "worker_invalid_response", Message: "The Python data worker returned no result."}
	}
	if err := json.Unmarshal(response.Result, result); err != nil {
		return &RPCError{Code: "worker_invalid_response", Message: "The Python data worker result did not match the adapter contract.", Cause: fmt.Errorf("decode worker result: %w", err)}
	}
	return nil
}
