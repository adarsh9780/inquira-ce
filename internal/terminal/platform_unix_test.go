//go:build !windows

package terminal

import (
	"context"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestPlatformTerminalRunsAnInteractiveShell(t *testing.T) {
	var mu sync.Mutex
	var output strings.Builder
	exited := make(chan struct{}, 1)
	service := NewPlatformService(func(name string, payload any) {
		switch name {
		case DataEventName:
			event := payload.(DataEvent)
			mu.Lock()
			output.WriteString(event.Data)
			mu.Unlock()
		case ExitEventName:
			select {
			case exited <- struct{}{}:
			default:
			}
		}
	})
	t.Cleanup(func() { _ = service.Close() })

	response, err := service.Start(context.Background(), StartRequest{
		SessionID: "integration", Cwd: t.TempDir(), Cols: 80, Rows: 24,
	})
	if err != nil {
		t.Fatal(err)
	}
	if response.Shell == "" {
		t.Fatal("shell name is empty")
	}
	if err := service.Write("integration", "printf 'inquira-pty-marker\\n'\nexit\n"); err != nil {
		t.Fatal(err)
	}
	select {
	case <-exited:
	case <-time.After(5 * time.Second):
		t.Fatal("interactive shell did not exit")
	}
	mu.Lock()
	terminalOutput := output.String()
	mu.Unlock()
	if !strings.Contains(terminalOutput, "inquira-pty-marker") {
		t.Fatalf("terminal output = %q", terminalOutput)
	}
}
