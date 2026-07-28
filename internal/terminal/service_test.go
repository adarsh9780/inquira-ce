package terminal

import (
	"bytes"
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

type fakeProcess struct {
	reader     *io.PipeReader
	output     *io.PipeWriter
	writes     bytes.Buffer
	mu         sync.Mutex
	resizes    [][2]int
	killed     bool
	waitResult chan error
}

func newFakeProcess() *fakeProcess {
	reader, output := io.Pipe()
	return &fakeProcess{reader: reader, output: output, waitResult: make(chan error, 1)}
}

func (p *fakeProcess) Read(target []byte) (int, error) { return p.reader.Read(target) }
func (p *fakeProcess) Write(value []byte) (int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.writes.Write(value)
}
func (p *fakeProcess) Resize(cols, rows int) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.resizes = append(p.resizes, [2]int{cols, rows})
	return nil
}
func (p *fakeProcess) Kill() error {
	p.mu.Lock()
	p.killed = true
	p.mu.Unlock()
	_ = p.output.Close()
	_ = p.reader.Close()
	select {
	case p.waitResult <- errors.New("killed"):
	default:
	}
	return nil
}
func (p *fakeProcess) Wait() error { return <-p.waitResult }

type fakeStart struct {
	process    Process
	shell      string
	err        error
	cwd        string
	cols, rows int
}

type fakeFactory struct {
	mu     sync.Mutex
	starts []*fakeStart
}

func (f *fakeFactory) Start(_ context.Context, cwd string, cols, rows int) (Process, string, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	start := f.starts[0]
	f.starts = f.starts[1:]
	start.cwd, start.cols, start.rows = cwd, cols, rows
	return start.process, start.shell, start.err
}

type capturedEvent struct {
	name    string
	payload any
}

type delayedWaitProcess struct {
	*fakeProcess
	killObserved chan struct{}
	releaseWait  chan struct{}
}

func newDelayedWaitProcess() *delayedWaitProcess {
	return &delayedWaitProcess{
		fakeProcess:  newFakeProcess(),
		killObserved: make(chan struct{}),
		releaseWait:  make(chan struct{}),
	}
}

func (p *delayedWaitProcess) Wait() error {
	err := <-p.waitResult
	close(p.killObserved)
	<-p.releaseWait
	return err
}

func TestTerminalSessionStreamsWritesResizesAndStops(t *testing.T) {
	process := newFakeProcess()
	start := &fakeStart{process: process, shell: "/bin/zsh"}
	factory := &fakeFactory{starts: []*fakeStart{start}}
	events := make(chan capturedEvent, 8)
	service := NewService(factory, func(name string, payload any) { events <- capturedEvent{name, payload} })
	t.Cleanup(func() { _ = service.Close() })

	cwd := t.TempDir()
	response, err := service.Start(context.Background(), StartRequest{
		SessionID: "workspace:one", Cwd: cwd, Cols: 0, Rows: 900,
	})
	if err != nil {
		t.Fatal(err)
	}
	if response.SessionID != "workspace:one" || response.Cwd != cwd || response.Shell != "/bin/zsh" {
		t.Fatalf("start response = %#v", response)
	}
	if start.cwd != cwd || start.cols != 1 || start.rows != 500 {
		t.Fatalf("normalized start = %#v", start)
	}
	if _, err := process.output.Write([]byte("hello\r\n")); err != nil {
		t.Fatal(err)
	}
	event := waitTerminalEvent(t, events, DataEventName)
	if payload, ok := event.payload.(DataEvent); !ok || payload.SessionID != "workspace:one" || payload.Data != "hello\r\n" {
		t.Fatalf("data event = %#v", event)
	}
	if err := service.Write("workspace:one", "echo test\r"); err != nil {
		t.Fatal(err)
	}
	if err := service.Resize("workspace:one", 140, 40); err != nil {
		t.Fatal(err)
	}
	process.mu.Lock()
	if process.writes.String() != "echo test\r" || len(process.resizes) != 1 || process.resizes[0] != [2]int{140, 40} {
		process.mu.Unlock()
		t.Fatalf("process input = %q, resizes = %#v", process.writes.String(), process.resizes)
	}
	process.mu.Unlock()
	stopped, err := service.Stop("workspace:one")
	if err != nil || !stopped {
		t.Fatalf("Stop() = %v, %v", stopped, err)
	}
	waitTerminalEvent(t, events, ExitEventName)
	stopped, err = service.Stop("workspace:one")
	if err != nil || stopped {
		t.Fatalf("second Stop() = %v, %v", stopped, err)
	}
	if err := service.Write("workspace:one", "pwd\r"); !errors.Is(err, ErrSessionNotFound) {
		t.Fatalf("missing write error = %v", err)
	}
}

func TestTerminalStopWaitsForProcessCleanup(t *testing.T) {
	process := newDelayedWaitProcess()
	factory := &fakeFactory{starts: []*fakeStart{{process: process, shell: "/bin/zsh"}}}
	service := NewService(factory, nil)
	t.Cleanup(func() { _ = service.Close() })

	if _, err := service.Start(context.Background(), StartRequest{
		SessionID: "workspace:one", Cwd: t.TempDir(), Cols: 80, Rows: 24,
	}); err != nil {
		t.Fatal(err)
	}

	type stopResult struct {
		stopped bool
		err     error
	}
	result := make(chan stopResult, 1)
	go func() {
		stopped, err := service.Stop("workspace:one")
		result <- stopResult{stopped: stopped, err: err}
	}()

	select {
	case <-process.killObserved:
	case <-time.After(2 * time.Second):
		t.Fatal("process did not begin waiting for cleanup")
	}
	select {
	case returned := <-result:
		t.Fatalf("Stop returned before process cleanup completed: %#v", returned)
	default:
	}

	close(process.releaseWait)
	select {
	case returned := <-result:
		if returned.err != nil || !returned.stopped {
			t.Fatalf("Stop() = %#v", returned)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Stop did not return after process cleanup completed")
	}
}

func TestTerminalSessionReplacementCannotRemoveNewProcess(t *testing.T) {
	first, second := newFakeProcess(), newFakeProcess()
	factory := &fakeFactory{starts: []*fakeStart{
		{process: first, shell: "first-shell"},
		{process: second, shell: "second-shell"},
	}}
	events := make(chan capturedEvent, 8)
	service := NewService(factory, func(name string, payload any) { events <- capturedEvent{name, payload} })
	t.Cleanup(func() { _ = service.Close() })
	cwd := t.TempDir()

	if _, err := service.Start(context.Background(), StartRequest{SessionID: "same", Cwd: cwd, Cols: 80, Rows: 24}); err != nil {
		t.Fatal(err)
	}
	response, err := service.Start(context.Background(), StartRequest{SessionID: "same", Cwd: cwd, Cols: 90, Rows: 30})
	if err != nil || response.Shell != "second-shell" {
		t.Fatalf("replacement = %#v, %v", response, err)
	}
	waitTerminalEvent(t, events, ExitEventName)
	if err := service.Write("same", "new session"); err != nil {
		t.Fatalf("replacement was removed: %v", err)
	}
	first.mu.Lock()
	firstKilled := first.killed
	first.mu.Unlock()
	second.mu.Lock()
	secondInput := second.writes.String()
	second.mu.Unlock()
	if !firstKilled || secondInput != "new session" {
		t.Fatalf("first killed = %v, second input = %q", firstKilled, secondInput)
	}
}

func TestTerminalSessionRejectsInvalidIdentityAndWorkingDirectory(t *testing.T) {
	service := NewService(&fakeFactory{}, nil)
	for _, request := range []StartRequest{
		{SessionID: "", Cwd: t.TempDir()},
		{SessionID: "valid", Cwd: filepath.Join(t.TempDir(), "missing")},
	} {
		if _, err := service.Start(context.Background(), request); err == nil {
			t.Fatalf("Start(%#v) unexpectedly succeeded", request)
		}
	}
	file := filepath.Join(t.TempDir(), "file")
	if err := os.WriteFile(file, []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := service.Start(context.Background(), StartRequest{SessionID: "valid", Cwd: file}); err == nil {
		t.Fatal("file working directory unexpectedly succeeded")
	}
}

func waitTerminalEvent(t *testing.T, events <-chan capturedEvent, name string) capturedEvent {
	t.Helper()
	deadline := time.After(2 * time.Second)
	for {
		select {
		case event := <-events:
			if event.name == name {
				return event
			}
		case <-deadline:
			t.Fatalf("timed out waiting for %s", name)
		}
	}
}
