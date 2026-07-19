package dataworkerbundle

import (
	"embed"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
)

//go:embed pyproject.toml uv.lock all:src/inquira_data_worker
var projectFiles embed.FS

// Extract writes the version of the worker bundled with this executable.
func Extract(target string) error {
	if err := os.MkdirAll(target, 0o700); err != nil {
		return fmt.Errorf("create worker project directory: %w", err)
	}
	return fs.WalkDir(projectFiles, ".", func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if path == "." {
			return nil
		}
		destination := filepath.Join(target, filepath.FromSlash(path))
		if entry.IsDir() {
			return os.MkdirAll(destination, 0o700)
		}
		content, err := projectFiles.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read bundled worker file %s: %w", path, err)
		}
		temporary := destination + ".tmp"
		if err := os.WriteFile(temporary, content, 0o600); err != nil {
			return fmt.Errorf("write worker file %s: %w", path, err)
		}
		if err := os.Rename(temporary, destination); err != nil {
			return fmt.Errorf("publish worker file %s: %w", path, err)
		}
		return nil
	})
}
