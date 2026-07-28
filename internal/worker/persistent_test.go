package worker

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"sync"
	"testing"
	"time"
)

func TestPersistentTransportReusesProcessAndRoutesEvents(t *testing.T) {
	transport := newHelperTransport(t)
	defer transport.Close()
	ctx := context.Background()
	var first, second struct {
		PID   int    `json:"pid"`
		Value string `json:"value"`
	}
	events := make([]Event, 0)
	if err := transport.CallWithEvents(ctx, "echo", map[string]any{"value": "first"}, &first, func(event Event) {
		events = append(events, event)
	}); err != nil {
		t.Fatal(err)
	}
	if err := transport.Call(ctx, "echo", map[string]any{"value": "second"}, &second); err != nil {
		t.Fatal(err)
	}
	if first.PID == 0 || first.PID != second.PID {
		t.Fatalf("worker process was not reused: first=%#v second=%#v", first, second)
	}
	if first.Value != "first" || second.Value != "second" || len(events) != 1 || events[0].Type != "progress" {
		t.Fatalf("responses=%#v %#v events=%#v", first, second, events)
	}
}

func TestPersistentTransportRoutesConcurrentResponsesByRequestID(t *testing.T) {
	transport := newHelperTransport(t)
	defer transport.Close()
	ctx := context.Background()
	values := []string{"slow", "fast"}
	results := make(chan string, len(values))
	errorsSeen := make(chan error, len(values))
	var group sync.WaitGroup
	for _, value := range values {
		group.Add(1)
		go func(value string) {
			defer group.Done()
			var response struct {
				Value string `json:"value"`
			}
			if err := transport.Call(ctx, "echo", map[string]any{"value": value}, &response); err != nil {
				errorsSeen <- err
				return
			}
			results <- response.Value
		}(value)
	}
	group.Wait()
	close(results)
	close(errorsSeen)
	for err := range errorsSeen {
		t.Fatal(err)
	}
	seen := map[string]bool{}
	for value := range results {
		seen[value] = true
	}
	if !seen["slow"] || !seen["fast"] {
		t.Fatalf("routed values = %#v", seen)
	}
}

func TestPersistentTransportCancellationDoesNotPoisonWorker(t *testing.T) {
	transport := newHelperTransport(t)
	defer transport.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel()
	if err := transport.Call(ctx, "wait", map[string]any{}, &struct{}{}); errorCode(err) != "worker_cancelled" {
		t.Fatalf("cancelled call error = %v", err)
	}
	var response struct {
		Value string `json:"value"`
	}
	if err := transport.Call(context.Background(), "echo", map[string]any{"value": "alive"}, &response); err != nil {
		t.Fatal(err)
	}
	if response.Value != "alive" {
		t.Fatalf("response = %#v", response)
	}
}

func TestPersistentTransportRestartsAfterWorkerCrash(t *testing.T) {
	transport := newHelperTransport(t)
	defer transport.Close()
	var before struct {
		PID int `json:"pid"`
	}
	if err := transport.Call(context.Background(), "echo", map[string]any{"value": "before"}, &before); err != nil {
		t.Fatal(err)
	}
	if err := transport.Call(context.Background(), "crash", map[string]any{}, &struct{}{}); errorCode(err) != "worker_process_failed" {
		t.Fatalf("crash error = %v", err)
	}
	deadline := time.Now().Add(2 * time.Second)
	for transport.Running() && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	var after struct {
		PID   int    `json:"pid"`
		Value string `json:"value"`
	}
	if err := transport.Call(context.Background(), "echo", map[string]any{"value": "after"}, &after); err != nil {
		t.Fatal(err)
	}
	if before.PID == 0 || after.PID == 0 || before.PID == after.PID || after.Value != "after" {
		t.Fatalf("worker did not recover: before=%#v after=%#v", before, after)
	}
}

func TestPersistentTransportRestartsAfterExplicitStop(t *testing.T) {
	transport := newHelperTransport(t)
	defer transport.Close()
	var before struct {
		PID int `json:"pid"`
	}
	if err := transport.Call(context.Background(), "echo", map[string]any{"value": "before"}, &before); err != nil {
		t.Fatal(err)
	}
	if err := transport.Stop(); err != nil {
		t.Fatal(err)
	}
	var after struct {
		PID int `json:"pid"`
	}
	if err := transport.Call(context.Background(), "echo", map[string]any{"value": "after"}, &after); err != nil {
		t.Fatal(err)
	}
	if before.PID == 0 || after.PID == 0 || before.PID == after.PID {
		t.Fatalf("worker did not restart after stop: before=%#v after=%#v", before, after)
	}
}

func TestPersistentTransportRejectsUnavailableRuntimeAndCallsAfterClose(t *testing.T) {
	transport := NewPersistentTransport(Config{ReadinessCheck: func() bool { return false }})
	if err := transport.Call(context.Background(), "ping", map[string]any{}, &struct{}{}); errorCode(err) != "runtime_not_ready" {
		t.Fatalf("unready error = %v", err)
	}
	transport = newHelperTransport(t)
	if err := transport.Close(); err != nil {
		t.Fatal(err)
	}
	if err := transport.Call(context.Background(), "ping", map[string]any{}, &struct{}{}); errorCode(err) != "worker_closed" {
		t.Fatalf("closed error = %v", err)
	}
}

func newHelperTransport(t *testing.T) *PersistentTransport {
	t.Helper()
	transport := NewPersistentTransport(Config{PythonExecutable: os.Args[0], WorkerSourceDir: t.TempDir()})
	transport.newCommand = func() *exec.Cmd {
		command := exec.Command(os.Args[0], "-test.run=TestPersistentTransportHelperProcess", "--")
		command.Env = append(os.Environ(), "GO_WANT_WORKER_HELPER=1")
		return command
	}
	return transport
}

func TestPersistentTransportHelperProcess(t *testing.T) {
	if os.Getenv("GO_WANT_WORKER_HELPER") != "1" {
		return
	}
	encoder := json.NewEncoder(os.Stdout)
	var output sync.Mutex
	var group sync.WaitGroup
	for scanner := bufio.NewScanner(os.Stdin); scanner.Scan(); {
		var request struct {
			ID     string         `json:"id"`
			Method string         `json:"method"`
			Params map[string]any `json:"params"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &request); err != nil {
			os.Exit(2)
		}
		group.Add(1)
		go func() {
			defer group.Done()
			if request.Method == "crash" {
				os.Exit(23)
			}
			if request.Method == "wait" || request.Params["value"] == "slow" {
				time.Sleep(80 * time.Millisecond)
			}
			output.Lock()
			defer output.Unlock()
			if request.Method == "echo" {
				_ = encoder.Encode(map[string]any{"id": request.ID, "event": map[string]any{"type": "progress", "data": map[string]any{"stage": "echo"}}})
			}
			_ = encoder.Encode(map[string]any{
				"id":     request.ID,
				"result": map[string]any{"pid": os.Getpid(), "value": fmt.Sprint(request.Params["value"])},
				"error":  nil,
			})
		}()
	}
	group.Wait()
	os.Exit(0)
}

func errorCode(err error) string {
	if rpcError, ok := err.(*RPCError); ok {
		return rpcError.Code
	}
	return ""
}
