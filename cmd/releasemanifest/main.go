package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

var releaseVersionPattern = regexp.MustCompile(`^\d+\.\d+\.\d+$`)

type releaseConfig struct {
	Version         string
	MacOSPath       string
	WindowsPath     string
	OutputDirectory string
	BaseURL         string
	ReleaseNotesURL string
	PublishedAt     time.Time
}

type downloadManifest struct {
	SchemaVersion       int    `json:"schema_version"`
	Product             string `json:"product"`
	Version             string `json:"version"`
	MacOSARM64URL       string `json:"macos_arm64_url"`
	WindowsX64URL       string `json:"windows_x64_url"`
	PublishedAt         string `json:"published_at"`
	ReleaseNotesURL     string `json:"release_notes_url"`
	MacOSARM64SHA256    string `json:"macos_arm64_sha256"`
	WindowsX64SHA256    string `json:"windows_x64_sha256"`
	SHA256SUMSURL       string `json:"sha256sums_url"`
	SourceRepositoryURL string `json:"source_repository_url"`
}

type stagedRelease struct {
	Tag                 string
	VersionDirectory    string
	LatestManifestPath  string
	VersionManifestPath string
	ChecksumsPath       string
	MacOSPath           string
	WindowsPath         string
	Manifest            downloadManifest
}

func normalizeReleaseVersion(raw string) (tag string, version string, err error) {
	version = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(raw), "v"))
	if !releaseVersionPattern.MatchString(version) {
		return "", "", fmt.Errorf("release version %q must use Major.Minor.Patch, for example 0.6.0", raw)
	}
	return "v" + version, version, nil
}

func validateHTTPSURL(name, raw string) (string, error) {
	value := strings.TrimSpace(strings.TrimRight(raw, "/"))
	parsed, err := url.Parse(value)
	if err != nil || parsed.Scheme != "https" || parsed.Host == "" {
		return "", fmt.Errorf("%s must be an absolute HTTPS URL", name)
	}
	return value, nil
}

func validateInstaller(path, extension, platform string) error {
	if strings.TrimSpace(path) == "" {
		return fmt.Errorf("%s installer path is required", platform)
	}
	if !strings.EqualFold(filepath.Ext(path), extension) {
		return fmt.Errorf("%s installer must use the %s extension", platform, extension)
	}
	fileInfo, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("inspect %s installer: %w", platform, err)
	}
	if !fileInfo.Mode().IsRegular() {
		return fmt.Errorf("%s installer must be a regular file", platform)
	}
	return nil
}

func sha256File(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

func copyFile(source, destination string) error {
	input, err := os.Open(source)
	if err != nil {
		return err
	}
	defer input.Close()

	output, err := os.OpenFile(destination, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
	if err != nil {
		return err
	}
	if _, err := io.Copy(output, input); err != nil {
		_ = output.Close()
		return err
	}
	return output.Close()
}

func writeJSON(path string, value any) error {
	content, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	content = append(content, '\n')
	return os.WriteFile(path, content, 0o644)
}

func stageRelease(config releaseConfig) (stagedRelease, error) {
	tag, version, err := normalizeReleaseVersion(config.Version)
	if err != nil {
		return stagedRelease{}, err
	}
	if err := validateInstaller(config.MacOSPath, ".dmg", "macOS"); err != nil {
		return stagedRelease{}, err
	}
	if err := validateInstaller(config.WindowsPath, ".exe", "Windows"); err != nil {
		return stagedRelease{}, err
	}

	baseURL, err := validateHTTPSURL("base URL", config.BaseURL)
	if err != nil {
		return stagedRelease{}, err
	}
	releaseNotesURL, err := validateHTTPSURL("release notes URL", config.ReleaseNotesURL)
	if err != nil {
		return stagedRelease{}, err
	}
	if strings.TrimSpace(config.OutputDirectory) == "" {
		return stagedRelease{}, errors.New("output directory is required")
	}

	publishedAt := config.PublishedAt.UTC()
	if publishedAt.IsZero() {
		publishedAt = time.Now().UTC()
	}

	versionDirectory := filepath.Join(config.OutputDirectory, tag)
	if err := os.MkdirAll(versionDirectory, 0o755); err != nil {
		return stagedRelease{}, fmt.Errorf("create release staging directory: %w", err)
	}

	macOSName := filepath.Base(config.MacOSPath)
	windowsName := filepath.Base(config.WindowsPath)
	stagedMacOSPath := filepath.Join(versionDirectory, macOSName)
	stagedWindowsPath := filepath.Join(versionDirectory, windowsName)
	if err := copyFile(config.MacOSPath, stagedMacOSPath); err != nil {
		return stagedRelease{}, fmt.Errorf("stage macOS installer: %w", err)
	}
	if err := copyFile(config.WindowsPath, stagedWindowsPath); err != nil {
		return stagedRelease{}, fmt.Errorf("stage Windows installer: %w", err)
	}

	macOSSHA256, err := sha256File(stagedMacOSPath)
	if err != nil {
		return stagedRelease{}, fmt.Errorf("hash macOS installer: %w", err)
	}
	windowsSHA256, err := sha256File(stagedWindowsPath)
	if err != nil {
		return stagedRelease{}, fmt.Errorf("hash Windows installer: %w", err)
	}

	manifest := downloadManifest{
		SchemaVersion:       1,
		Product:             "inquira-go",
		Version:             version,
		MacOSARM64URL:       fmt.Sprintf("%s/%s/%s", baseURL, tag, url.PathEscape(macOSName)),
		WindowsX64URL:       fmt.Sprintf("%s/%s/%s", baseURL, tag, url.PathEscape(windowsName)),
		PublishedAt:         publishedAt.Format(time.RFC3339),
		ReleaseNotesURL:     releaseNotesURL,
		MacOSARM64SHA256:    macOSSHA256,
		WindowsX64SHA256:    windowsSHA256,
		SHA256SUMSURL:       fmt.Sprintf("%s/%s/SHA256SUMS.txt", baseURL, tag),
		SourceRepositoryURL: "https://github.com/adarsh9780/inquira-ce",
	}

	latestManifestPath := filepath.Join(config.OutputDirectory, "latest.json")
	versionManifestPath := filepath.Join(versionDirectory, "manifest.json")
	if err := writeJSON(latestManifestPath, manifest); err != nil {
		return stagedRelease{}, fmt.Errorf("write latest manifest: %w", err)
	}
	if err := writeJSON(versionManifestPath, manifest); err != nil {
		return stagedRelease{}, fmt.Errorf("write version manifest: %w", err)
	}

	checksumsPath := filepath.Join(versionDirectory, "SHA256SUMS.txt")
	checksums := fmt.Sprintf("%s  %s\n%s  %s\n", macOSSHA256, macOSName, windowsSHA256, windowsName)
	if err := os.WriteFile(checksumsPath, []byte(checksums), 0o644); err != nil {
		return stagedRelease{}, fmt.Errorf("write checksums: %w", err)
	}

	return stagedRelease{
		Tag:                 tag,
		VersionDirectory:    versionDirectory,
		LatestManifestPath:  latestManifestPath,
		VersionManifestPath: versionManifestPath,
		ChecksumsPath:       checksumsPath,
		MacOSPath:           stagedMacOSPath,
		WindowsPath:         stagedWindowsPath,
		Manifest:            manifest,
	}, nil
}

func main() {
	version := flag.String("version", "", "release version, with or without a leading v")
	macOSPath := flag.String("macos", "", "path to the macOS ARM64 DMG")
	windowsPath := flag.String("windows", "", "path to the Windows x64 installer")
	outputDirectory := flag.String("output", "release-stage", "directory in which to stage public download objects")
	baseURL := flag.String("base-url", "https://downloads.inquiraai.com", "public downloads base URL")
	releaseNotesURL := flag.String("release-notes-url", "", "public release notes URL")
	publishedAtRaw := flag.String("published-at", "", "optional RFC3339 publication time")
	flag.Parse()

	var publishedAt time.Time
	var err error
	if strings.TrimSpace(*publishedAtRaw) != "" {
		publishedAt, err = time.Parse(time.RFC3339, strings.TrimSpace(*publishedAtRaw))
		if err != nil {
			fmt.Fprintln(os.Stderr, "published-at must use RFC3339")
			os.Exit(1)
		}
	}

	staged, err := stageRelease(releaseConfig{
		Version:         *version,
		MacOSPath:       *macOSPath,
		WindowsPath:     *windowsPath,
		OutputDirectory: *outputDirectory,
		BaseURL:         *baseURL,
		ReleaseNotesURL: *releaseNotesURL,
		PublishedAt:     publishedAt,
	})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	fmt.Printf("Staged %s public downloads in %s.\n", staged.Tag, staged.VersionDirectory)
}
