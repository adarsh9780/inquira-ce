package runtimeprovision

import (
	"fmt"
	"net/url"
	"strings"
)

// Mode selects who supplies Python and where UV downloads approved artifacts.
type Mode string

const (
	ModeManaged        Mode = "managed"
	ModeExternalPython Mode = "external-python"
	ModeInternalMirror Mode = "internal-mirror"
)

// Config is a transient provisioning request. Proxy and index URLs may contain
// credentials, so callers must not persist the complete value.
type Config struct {
	Mode                Mode   `json:"mode"`
	PythonVersion       string `json:"pythonVersion"`
	PythonExecutable    string `json:"pythonExecutable,omitempty"`
	PythonInstallMirror string `json:"pythonInstallMirror,omitempty"`
	DefaultIndex        string `json:"defaultIndex,omitempty"`
	UseSystemCerts      bool   `json:"useSystemCertificates"`
	HTTPProxy           string `json:"httpProxy,omitempty"`
	HTTPSProxy          string `json:"httpsProxy,omitempty"`
	NoProxy             string `json:"noProxy,omitempty"`
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
	if err := validateProxyURL("HTTP proxy", c.HTTPProxy); err != nil {
		return err
	}
	if err := validateProxyURL("HTTPS proxy", c.HTTPSProxy); err != nil {
		return err
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

func validateProxyURL(label, value string) error {
	normalized := strings.TrimSpace(value)
	if normalized == "" {
		return nil
	}
	parsed, err := url.Parse(normalized)
	if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" {
		return fmt.Errorf("%s must be a valid HTTP or HTTPS URL", label)
	}
	return nil
}
