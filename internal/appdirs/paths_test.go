package appdirs

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFromRootAndEnsure(t *testing.T) {
	root := filepath.Join(t.TempDir(), "custom", "Inquira")
	paths := FromRoot(root)

	if paths.DatabasePath != filepath.Join(root, "data", "inquira.db") {
		t.Fatalf("unexpected database path: %s", paths.DatabasePath)
	}
	if paths.LogsDir != filepath.Join(root, "data", "logs") {
		t.Fatalf("unexpected logs path: %s", paths.LogsDir)
	}
	if err := paths.Ensure(); err != nil {
		t.Fatalf("Ensure() error = %v", err)
	}
	for _, directory := range []string{paths.ConfigDir, paths.DataDir, paths.RuntimeDir, paths.LogsDir} {
		info, err := os.Stat(directory)
		if err != nil {
			t.Fatalf("stat %s: %v", directory, err)
		}
		if !info.IsDir() {
			t.Fatalf("%s is not a directory", directory)
		}
	}
}

func TestResolveUsesConfiguredApplicationRoot(t *testing.T) {
	root := filepath.Join(t.TempDir(), "approved-location", "Inquira")
	t.Setenv(rootEnvironmentVariable, root)

	paths, err := Resolve()
	if err != nil {
		t.Fatalf("Resolve() error = %v", err)
	}
	if paths.ConfigDir != filepath.Clean(root) {
		t.Fatalf("ConfigDir = %q, want %q", paths.ConfigDir, root)
	}
	if paths.RuntimeDir != filepath.Join(root, "runtime") {
		t.Fatalf("RuntimeDir = %q", paths.RuntimeDir)
	}
}
