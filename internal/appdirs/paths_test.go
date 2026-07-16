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
	if err := paths.Ensure(); err != nil {
		t.Fatalf("Ensure() error = %v", err)
	}
	for _, directory := range []string{paths.ConfigDir, paths.DataDir, paths.RuntimeDir} {
		info, err := os.Stat(directory)
		if err != nil {
			t.Fatalf("stat %s: %v", directory, err)
		}
		if !info.IsDir() {
			t.Fatalf("%s is not a directory", directory)
		}
	}
}
