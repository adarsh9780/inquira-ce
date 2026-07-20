package runtimeprovision

import (
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
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
	CertificateBundle   string `json:"certificateBundle,omitempty"`
	HTTPProxy           string `json:"httpProxy,omitempty"`
	HTTPSProxy          string `json:"httpsProxy,omitempty"`
	NoProxy             string `json:"noProxy,omitempty"`
}

// SavedConfig is the non-secret subset retained after successful setup. URLs
// used for indexes, mirrors, and proxies are deliberately excluded.
type SavedConfig struct {
	Mode              Mode   `json:"mode"`
	PythonVersion     string `json:"pythonVersion,omitempty"`
	PythonExecutable  string `json:"pythonExecutable,omitempty"`
	UseSystemCerts    bool   `json:"useSystemCertificates"`
	CertificateBundle string `json:"certificateBundle,omitempty"`
}

var compatiblePythonVersion = regexp.MustCompile(`^3\.12(?:\.\d+)?$`)

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
	if strings.ContainsAny(c.NoProxy, "\r\n") {
		return fmt.Errorf("proxy bypass list may not contain line breaks")
	}
	if err := validateHTTPURL("python install mirror", c.PythonInstallMirror); err != nil {
		return err
	}
	if err := validateHTTPURL("default package index", c.DefaultIndex); err != nil {
		return err
	}
	if err := validateCertificateBundle(c.CertificateBundle); err != nil {
		return err
	}

	switch c.Mode {
	case ModeManaged:
		if !compatiblePythonVersion.MatchString(strings.TrimSpace(c.PythonVersion)) {
			return fmt.Errorf("managed mode requires Python 3.12")
		}
	case ModeExternalPython:
		if err := validatePythonExecutable(c.PythonExecutable); err != nil {
			return err
		}
	case ModeInternalMirror:
		if !compatiblePythonVersion.MatchString(strings.TrimSpace(c.PythonVersion)) {
			return fmt.Errorf("internal-mirror mode requires Python 3.12")
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

func savedConfigFrom(config Config) SavedConfig {
	return SavedConfig{
		Mode:              config.Mode,
		PythonVersion:     strings.TrimSpace(config.PythonVersion),
		PythonExecutable:  strings.TrimSpace(config.PythonExecutable),
		UseSystemCerts:    config.UseSystemCerts,
		CertificateBundle: strings.TrimSpace(config.CertificateBundle),
	}
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

func validateHTTPURL(label, value string) error {
	normalized := strings.TrimSpace(value)
	if normalized == "" {
		return nil
	}
	parsed, err := url.Parse(normalized)
	if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" || parsed.Fragment != "" {
		return fmt.Errorf("%s must be a valid HTTP or HTTPS URL without a fragment", label)
	}
	return nil
}

func validatePythonExecutable(value string) error {
	path := strings.TrimSpace(value)
	if path == "" {
		return fmt.Errorf("python executable is required for external-python mode")
	}
	if !filepath.IsAbs(path) {
		return fmt.Errorf("python executable must be an absolute path")
	}
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("python executable is not accessible: %w", err)
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("python executable must be a regular file")
	}
	if runtime.GOOS != "windows" && info.Mode().Perm()&0o111 == 0 {
		return fmt.Errorf("python executable is not executable")
	}
	return nil
}

func validateCertificateBundle(value string) error {
	path := strings.TrimSpace(value)
	if path == "" {
		return nil
	}
	if !filepath.IsAbs(path) {
		return fmt.Errorf("certificate bundle must be an absolute path")
	}
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("certificate bundle is not accessible: %w", err)
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("certificate bundle must be a regular file")
	}
	return nil
}
