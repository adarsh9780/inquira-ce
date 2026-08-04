package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestReadVersionAcceptsStableCanonicalValue(t *testing.T) {
	versionPath := filepath.Join(t.TempDir(), "VERSION")
	if err := os.WriteFile(versionPath, []byte("0.6.0\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	version, err := readVersion(versionPath)
	if err != nil || version != "0.6.0" {
		t.Fatalf("readVersion() = %q, %v", version, err)
	}
}

func TestReadVersionRejectsUnsupportedValues(t *testing.T) {
	for _, value := range []string{"", "0.6", "v0.6.0", "0.6.0-beta.1", "1.2.3.4"} {
		t.Run(value, func(t *testing.T) {
			versionPath := filepath.Join(t.TempDir(), "VERSION")
			if err := os.WriteFile(versionPath, []byte(value), 0o600); err != nil {
				t.Fatal(err)
			}
			if _, err := readVersion(versionPath); err == nil {
				t.Fatalf("readVersion(%q) unexpectedly succeeded", value)
			}
		})
	}
}

func TestGenerateWailsConfigUsesOnlyCanonicalVersion(t *testing.T) {
	directory := t.TempDir()
	versionPath := filepath.Join(directory, "VERSION")
	templatePath := filepath.Join(directory, "wails.template.json")
	outputPath := filepath.Join(directory, "wails.json")
	if err := os.WriteFile(versionPath, []byte("0.6.0\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	template := `{"name":"inquira-go","info":{"companyName":"Inquira"}}`
	if err := os.WriteFile(templatePath, []byte(template), 0o600); err != nil {
		t.Fatal(err)
	}
	version, err := generateWailsConfig(versionPath, templatePath, outputPath)
	if err != nil || version != "0.6.0" {
		t.Fatalf("generateWailsConfig() = %q, %v", version, err)
	}
	content, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatal(err)
	}
	var configuration map[string]any
	if err := json.Unmarshal(content, &configuration); err != nil {
		t.Fatal(err)
	}
	info := configuration["info"].(map[string]any)
	if configuration["name"] != "inquira-go" || info["companyName"] != "Inquira" || info["productVersion"] != "0.6.0" {
		t.Fatalf("generated Wails configuration = %#v", configuration)
	}
	fileInfo, err := os.Stat(outputPath)
	if err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS != "windows" && fileInfo.Mode().Perm() != 0o644 {
		t.Fatalf("permissions = %o, want 644", fileInfo.Mode().Perm())
	}

	if err := os.WriteFile(versionPath, []byte("0.6.1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := generateWailsConfig(versionPath, templatePath, outputPath); err != nil {
		t.Fatalf("replace generated configuration: %v", err)
	}
	updated, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(updated, &configuration); err != nil {
		t.Fatal(err)
	}
	if configuration["info"].(map[string]any)["productVersion"] != "0.6.1" {
		t.Fatalf("updated Wails configuration = %#v", configuration)
	}
}

func TestRenderWailsConfigRejectsDuplicateVersion(t *testing.T) {
	template := []byte(`{"info":{"productVersion":"9.9.9"}}`)
	if _, err := renderWailsConfig(template, "0.6.0"); err == nil {
		t.Fatal("template productVersion unexpectedly accepted")
	}
}
