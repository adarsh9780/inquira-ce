package runtimeprovision

import (
	"fmt"
	"strings"
)

// Mode selects who supplies Python and where UV downloads approved artifacts.
type Mode string

const (
	ModeManaged        Mode = "managed"
	ModeExternalPython Mode = "external-python"
	ModeInternalMirror Mode = "internal-mirror"
)

// Config is safe to persist. Credentials for private indexes must be supplied
// separately through the operating-system keychain or process environment.
type Config struct {
	Mode                Mode   `json:"mode"`
	PythonVersion       string `json:"pythonVersion"`
	PythonExecutable    string `json:"pythonExecutable,omitempty"`
	PythonInstallMirror string `json:"pythonInstallMirror,omitempty"`
	DefaultIndex        string `json:"defaultIndex,omitempty"`
	UseSystemCerts      bool   `json:"useSystemCertificates"`
}

func DefaultConfig() Config {
	return Config{
		Mode:           ModeManaged,
		PythonVersion:  "3.12",
		UseSystemCerts: false,
	}
}

func SupportedModes() []Mode {
	return []Mode{ModeManaged, ModeExternalPython, ModeInternalMirror}
}

func (c Config) Validate() error {
	if c.Mode == "" {
		return fmt.Errorf("runtime mode is required")
	}

	switch c.Mode {
	case ModeManaged:
		if strings.TrimSpace(c.PythonVersion) == "" {
			return fmt.Errorf("python version is required for managed mode")
		}
	case ModeExternalPython:
		if strings.TrimSpace(c.PythonExecutable) == "" {
			return fmt.Errorf("python executable is required for external-python mode")
		}
	case ModeInternalMirror:
		if strings.TrimSpace(c.PythonVersion) == "" {
			return fmt.Errorf("python version is required for internal-mirror mode")
		}
		if strings.TrimSpace(c.PythonInstallMirror) == "" {
			return fmt.Errorf("python install mirror is required for internal-mirror mode")
		}
		if strings.TrimSpace(c.DefaultIndex) == "" {
			return fmt.Errorf("default package index is required for internal-mirror mode")
		}
	default:
		return fmt.Errorf("unsupported runtime mode %q", c.Mode)
	}

	return nil
}
