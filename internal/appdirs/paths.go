package appdirs

import (
	"fmt"
	"os"
	"path/filepath"
)

const appDirectoryName = "Inquira"

// Paths contains every application-owned path used by the Go control plane.
type Paths struct {
	ConfigDir    string `json:"config_dir"`
	DataDir      string `json:"data_dir"`
	RuntimeDir   string `json:"runtime_dir"`
	DatabasePath string `json:"database_path"`
}

// Resolve returns platform-appropriate paths without creating them.
func Resolve() (Paths, error) {
	configRoot, err := os.UserConfigDir()
	if err != nil {
		return Paths{}, fmt.Errorf("resolve user config directory: %w", err)
	}
	if configRoot == "" {
		return Paths{}, fmt.Errorf("resolve user config directory: empty path")
	}
	return FromRoot(filepath.Join(configRoot, appDirectoryName)), nil
}

// FromRoot builds a path set rooted at root. It is primarily useful for tests.
func FromRoot(root string) Paths {
	cleanRoot := filepath.Clean(root)
	dataDir := filepath.Join(cleanRoot, "data")
	return Paths{
		ConfigDir:    cleanRoot,
		DataDir:      dataDir,
		RuntimeDir:   filepath.Join(cleanRoot, "runtime"),
		DatabasePath: filepath.Join(dataDir, "inquira.db"),
	}
}

// Ensure creates all application-owned directories with user-only permissions.
func (p Paths) Ensure() error {
	for _, directory := range []string{p.ConfigDir, p.DataDir, p.RuntimeDir} {
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return fmt.Errorf("create application directory %q: %w", directory, err)
		}
	}
	return nil
}
