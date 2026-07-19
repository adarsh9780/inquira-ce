package dataworkerbundle

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestExtractWritesTheWorkerProjectAndIsRepeatable(t *testing.T) {
	target := filepath.Join(t.TempDir(), "worker")
	if err := Extract(target); err != nil {
		t.Fatalf("Extract() error = %v", err)
	}
	for _, relative := range []string{
		"pyproject.toml",
		"uv.lock",
		"src/inquira_data_worker/__main__.py",
		"src/inquira_data_worker/kernel.py",
		"src/inquira_data_worker/rpc.py",
		"src/inquira_data_worker/runtime.py",
		"src/inquira_data_worker/adapters/file.py",
	} {
		content, err := os.ReadFile(filepath.Join(target, relative))
		if err != nil || len(content) == 0 {
			t.Fatalf("extracted %s: bytes=%d error=%v", relative, len(content), err)
		}
	}
	if err := Extract(target); err != nil {
		t.Fatalf("repeat Extract() error = %v", err)
	}
	main, err := os.ReadFile(filepath.Join(target, "src/inquira_data_worker/__main__.py"))
	if err != nil || !strings.Contains(string(main), "WorkerRuntime") {
		t.Fatalf("unexpected main module: %v", err)
	}
}
