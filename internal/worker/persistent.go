package worker

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

type Config struct {
	PythonExecutable string
	WorkerSourceDir  string
	Environment      []string
	ReadinessCheck   func() bool
}

type Event struct {
	Type string          `json:"type"`
	Data json.RawMessage `json:"data"`
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
	if e.Message != "" {
		return e.Message
	}
	return e.Code
}

func (e *RPCError) Unwrap() error { return e.Cause }

type wireMessage struct {
	ID     string          `json:"id"`
	Result json.RawMessage `json:"result"`
	Error  *wireError      `json:"error"`
	Event  *Event          `json:"event"`
}

type wireError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

type pendingMessage struct {
	message wireMessage
	err     error
}

type managedProcess struct {
	command    *exec.Cmd
	stdin      io.WriteCloser
	generation uint64
	done       chan struct{}
}

type PersistentTransport struct {
	config Config

	mu         sync.Mutex
	writeMu    sync.Mutex
	process    *managedProcess
	pending    map[string]chan pendingMessage
	generation uint64
	closed     bool

	newCommand func() *exec.Cmd
}

func NewPersistentTransport(config Config) *PersistentTransport {
	config.PythonExecutable = strings.TrimSpace(config.PythonExecutable)
	config.WorkerSourceDir = strings.TrimSpace(config.WorkerSourceDir)
	transport := &PersistentTransport{config: config, pending: make(map[string]chan pendingMessage)}
	transport.newCommand = func() *exec.Cmd {
		command := exec.Command(config.PythonExecutable, "-m", "inquira_data_worker")
		command.Env = append(os.Environ(), append([]string{"PYTHONPATH=" + config.WorkerSourceDir}, config.Environment...)...)
		return command
	}
	return transport
}

func (t *PersistentTransport) Call(ctx context.Context, method string, params, result any) error {
	return t.CallWithEvents(ctx, method, params, result, nil)
}

func (t *PersistentTransport) Running() bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	return !t.closed && t.process != nil
}

func (t *PersistentTransport) CallWithEvents(
	ctx context.Context,
	method string,
	params, result any,
	emit func(Event),
) error {
	if ctx == nil {
		ctx = context.Background()
	}
	method = strings.TrimSpace(method)
	if method == "" {
		return &RPCError{Code: "worker_request_failed", Message: "Worker method is required."}
	}
	process, err := t.ensureProcess()
	if err != nil {
		return err
	}
	requestID := uuid.NewString()
	responseChannel := make(chan pendingMessage, 256)
	t.mu.Lock()
	if t.closed {
		t.mu.Unlock()
		return &RPCError{Code: "worker_closed", Message: "The Python worker is closed."}
	}
	if t.process != process {
		t.mu.Unlock()
		return &RPCError{Code: "worker_process_failed", Message: "The Python worker exited before the request started."}
	}
	t.pending[requestID] = responseChannel
	t.mu.Unlock()

	request := struct {
		ID     string `json:"id"`
		Method string `json:"method"`
		Params any    `json:"params"`
	}{ID: requestID, Method: method, Params: params}
	if err := t.writeRequest(process, request); err != nil {
		t.removePending(requestID)
		return &RPCError{Code: "worker_process_failed", Message: "Could not send a request to the Python worker.", Cause: err}
	}

	for {
		select {
		case <-ctx.Done():
			t.removePending(requestID)
			return &RPCError{Code: "worker_cancelled", Message: "The Python worker request was cancelled.", Cause: ctx.Err()}
		case received := <-responseChannel:
			if received.err != nil {
				t.removePending(requestID)
				return &RPCError{Code: "worker_process_failed", Message: "The Python worker exited unexpectedly.", Cause: received.err}
			}
			if received.message.Event != nil {
				if emit != nil {
					emit(*received.message.Event)
				}
				continue
			}
			t.removePending(requestID)
			if received.message.Error != nil {
				return &RPCError{Code: received.message.Error.Code, Message: received.message.Error.Message}
			}
			if len(received.message.Result) == 0 || string(received.message.Result) == "null" {
				return &RPCError{Code: "worker_invalid_response", Message: "The Python worker returned no result."}
			}
			if result == nil {
				return nil
			}
			if err := json.Unmarshal(received.message.Result, result); err != nil {
				return &RPCError{Code: "worker_invalid_response", Message: "The Python worker result did not match the requested contract.", Cause: err}
			}
			return nil
		}
	}
}

func (t *PersistentTransport) Close() error {
	t.mu.Lock()
	if t.closed {
		t.mu.Unlock()
		return nil
	}
	t.closed = true
	process := t.process
	t.process = nil
	pending := t.pending
	t.pending = make(map[string]chan pendingMessage)
	t.mu.Unlock()

	closedErr := errors.New("worker closed")
	for _, response := range pending {
		select {
		case response <- pendingMessage{err: closedErr}:
		default:
		}
	}
	if process == nil {
		return nil
	}
	_ = process.stdin.Close()
	select {
	case <-process.done:
		return nil
	case <-time.After(5 * time.Second):
		if err := process.command.Process.Kill(); err != nil && !errors.Is(err, os.ErrProcessDone) {
			return fmt.Errorf("stop Python worker: %w", err)
		}
		<-process.done
		return nil
	}
}

func (t *PersistentTransport) ensureProcess() (*managedProcess, error) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closed {
		return nil, &RPCError{Code: "worker_closed", Message: "The Python worker is closed."}
	}
	if t.config.ReadinessCheck != nil && !t.config.ReadinessCheck() {
		return nil, &RPCError{Code: "runtime_not_ready", Message: "Configure or update the Python data runtime before continuing."}
	}
	if t.process != nil {
		return t.process, nil
	}
	if t.config.PythonExecutable == "" || t.config.WorkerSourceDir == "" {
		return nil, &RPCError{Code: "runtime_not_ready", Message: "Configure the Python data runtime before continuing."}
	}
	if info, err := os.Stat(t.config.PythonExecutable); err != nil || !info.Mode().IsRegular() {
		return nil, &RPCError{Code: "runtime_not_ready", Message: "The configured Python executable is unavailable.", Cause: err}
	}
	if info, err := os.Stat(t.config.WorkerSourceDir); err != nil || !info.IsDir() {
		return nil, &RPCError{Code: "runtime_not_ready", Message: "The bundled Python worker is unavailable.", Cause: err}
	}
	command := t.newCommand()
	stdin, err := command.StdinPipe()
	if err != nil {
		return nil, &RPCError{Code: "worker_process_failed", Message: "Could not open Python worker input.", Cause: err}
	}
	stdout, err := command.StdoutPipe()
	if err != nil {
		_ = stdin.Close()
		return nil, &RPCError{Code: "worker_process_failed", Message: "Could not open Python worker output.", Cause: err}
	}
	stderr, err := command.StderrPipe()
	if err != nil {
		_ = stdin.Close()
		return nil, &RPCError{Code: "worker_process_failed", Message: "Could not open Python worker diagnostics.", Cause: err}
	}
	if err := command.Start(); err != nil {
		_ = stdin.Close()
		return nil, &RPCError{Code: "worker_process_failed", Message: "The Python worker could not be started.", Cause: err}
	}
	t.generation++
	process := &managedProcess{command: command, stdin: stdin, generation: t.generation, done: make(chan struct{})}
	t.process = process
	go t.readResponses(process, stdout)
	go func() { _, _ = io.Copy(io.Discard, stderr) }()
	go t.waitForProcess(process)
	return process, nil
}

func (t *PersistentTransport) writeRequest(process *managedProcess, request any) error {
	t.writeMu.Lock()
	defer t.writeMu.Unlock()
	t.mu.Lock()
	active := !t.closed && t.process == process
	t.mu.Unlock()
	if !active {
		return errors.New("worker process is not active")
	}
	return json.NewEncoder(process.stdin).Encode(request)
}

func (t *PersistentTransport) readResponses(process *managedProcess, output io.Reader) {
	decoder := json.NewDecoder(bufio.NewReader(output))
	for {
		var message wireMessage
		if err := decoder.Decode(&message); err != nil {
			t.mu.Lock()
			active := t.process == process
			t.mu.Unlock()
			if active {
				_ = process.command.Process.Kill()
			}
			return
		}
		if message.ID == "" {
			continue
		}
		t.mu.Lock()
		response := t.pending[message.ID]
		active := t.process == process
		t.mu.Unlock()
		if !active || response == nil {
			continue
		}
		response <- pendingMessage{message: message}
	}
}

func (t *PersistentTransport) waitForProcess(process *managedProcess) {
	err := process.command.Wait()
	close(process.done)
	t.mu.Lock()
	if t.process != process {
		t.mu.Unlock()
		return
	}
	t.process = nil
	pending := t.pending
	t.pending = make(map[string]chan pendingMessage)
	t.mu.Unlock()
	if err == nil {
		err = io.EOF
	}
	for _, response := range pending {
		select {
		case response <- pendingMessage{err: err}:
		default:
		}
	}
}

func (t *PersistentTransport) removePending(requestID string) {
	t.mu.Lock()
	delete(t.pending, requestID)
	t.mu.Unlock()
}
