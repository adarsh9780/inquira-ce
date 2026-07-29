package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestStageReleaseBuildsBackwardCompatibleManifest(t *testing.T) {
	t.Parallel()

	tempDirectory := t.TempDir()
	macOSPath := filepath.Join(tempDirectory, "Inquira-0.6.0-macOS-arm64.dmg")
	windowsPath := filepath.Join(tempDirectory, "Inquira-0.6.0-windows-x64-setup.exe")
	if err := os.WriteFile(macOSPath, []byte("macos-installer"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(windowsPath, []byte("windows-installer"), 0o644); err != nil {
		t.Fatal(err)
	}

	outputDirectory := filepath.Join(tempDirectory, "release")
	publishedAt := time.Date(2026, 7, 29, 1, 2, 3, 0, time.UTC)
	staged, err := stageRelease(releaseConfig{
		Version:         "v0.6.0",
		MacOSPath:       macOSPath,
		WindowsPath:     windowsPath,
		OutputDirectory: outputDirectory,
		BaseURL:         "https://downloads.inquiraai.com/",
		ReleaseNotesURL: "https://inquiraai.com/releases/v0.6.0",
		PublishedAt:     publishedAt,
	})
	if err != nil {
		t.Fatalf("stageRelease: %v", err)
	}

	if staged.Tag != "v0.6.0" || staged.Manifest.Version != "0.6.0" {
		t.Fatalf("unexpected release identity: %#v", staged)
	}
	if staged.Manifest.SchemaVersion != 1 || staged.Manifest.Product != "inquira-go" {
		t.Fatalf("unexpected manifest contract: %#v", staged.Manifest)
	}
	if staged.Manifest.PublishedAt != "2026-07-29T01:02:03Z" {
		t.Fatalf("published_at = %q", staged.Manifest.PublishedAt)
	}
	if staged.Manifest.MacOSARM64URL != "https://downloads.inquiraai.com/v0.6.0/Inquira-0.6.0-macOS-arm64.dmg" {
		t.Fatalf("macOS URL = %q", staged.Manifest.MacOSARM64URL)
	}
	if staged.Manifest.WindowsX64URL != "https://downloads.inquiraai.com/v0.6.0/Inquira-0.6.0-windows-x64-setup.exe" {
		t.Fatalf("Windows URL = %q", staged.Manifest.WindowsX64URL)
	}
	if staged.Manifest.SourceRepositoryURL != "https://github.com/adarsh9780/inquira-ce" {
		t.Fatalf("source repository URL = %q", staged.Manifest.SourceRepositoryURL)
	}
	if len(staged.Manifest.MacOSARM64SHA256) != 64 || len(staged.Manifest.WindowsX64SHA256) != 64 {
		t.Fatalf("missing checksums: %#v", staged.Manifest)
	}

	latestContent, err := os.ReadFile(staged.LatestManifestPath)
	if err != nil {
		t.Fatal(err)
	}
	var latest map[string]any
	if err := json.Unmarshal(latestContent, &latest); err != nil {
		t.Fatal(err)
	}
	for _, field := range []string{
		"version",
		"macos_arm64_url",
		"windows_x64_url",
		"published_at",
		"release_notes_url",
		"macos_arm64_sha256",
		"windows_x64_sha256",
	} {
		if _, ok := latest[field]; !ok {
			t.Fatalf("latest manifest is missing %q: %s", field, latestContent)
		}
	}

	checksums, err := os.ReadFile(staged.ChecksumsPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(checksums), filepath.Base(macOSPath)) ||
		!strings.Contains(string(checksums), filepath.Base(windowsPath)) {
		t.Fatalf("unexpected checksums file: %s", checksums)
	}

	for source, destination := range map[string]string{
		macOSPath:   staged.MacOSPath,
		windowsPath: staged.WindowsPath,
	} {
		sourceContent, err := os.ReadFile(source)
		if err != nil {
			t.Fatal(err)
		}
		destinationContent, err := os.ReadFile(destination)
		if err != nil {
			t.Fatal(err)
		}
		if string(destinationContent) != string(sourceContent) {
			t.Fatalf("staged content mismatch for %s", destination)
		}
	}
}

func TestStageReleaseRejectsUnsafeOrIncompleteInput(t *testing.T) {
	t.Parallel()

	tempDirectory := t.TempDir()
	macOSPath := filepath.Join(tempDirectory, "app.dmg")
	windowsPath := filepath.Join(tempDirectory, "app.exe")
	if err := os.WriteFile(macOSPath, []byte("mac"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(windowsPath, []byte("windows"), 0o644); err != nil {
		t.Fatal(err)
	}

	base := releaseConfig{
		Version:         "0.6.0",
		MacOSPath:       macOSPath,
		WindowsPath:     windowsPath,
		OutputDirectory: filepath.Join(tempDirectory, "release"),
		BaseURL:         "https://downloads.inquiraai.com",
		ReleaseNotesURL: "https://inquiraai.com/releases/v0.6.0",
	}

	tests := []struct {
		name   string
		mutate func(*releaseConfig)
	}{
		{name: "invalid version", mutate: func(config *releaseConfig) { config.Version = "0.6.0-beta.1" }},
		{name: "insecure base URL", mutate: func(config *releaseConfig) { config.BaseURL = "http://downloads.example.com" }},
		{name: "insecure release notes", mutate: func(config *releaseConfig) { config.ReleaseNotesURL = "file:///tmp/notes" }},
		{name: "wrong macOS extension", mutate: func(config *releaseConfig) { config.MacOSPath = windowsPath }},
		{name: "missing Windows installer", mutate: func(config *releaseConfig) { config.WindowsPath = filepath.Join(tempDirectory, "missing.exe") }},
	}

	for _, test := range tests {
		test := test
		t.Run(test.name, func(t *testing.T) {
			config := base
			config.OutputDirectory = filepath.Join(tempDirectory, strings.ReplaceAll(test.name, " ", "-"))
			test.mutate(&config)
			if _, err := stageRelease(config); err == nil {
				t.Fatal("stageRelease unexpectedly succeeded")
			}
		})
	}
}
