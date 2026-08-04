package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var stableVersionPattern = regexp.MustCompile(`^\d+\.\d+\.\d+$`)

func readVersion(path string) (string, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read application version: %w", err)
	}
	version := strings.TrimSpace(string(content))
	if !stableVersionPattern.MatchString(version) {
		return "", fmt.Errorf("application version %q must use Major.Minor.Patch, for example 0.6.0", version)
	}
	return version, nil
}

func renderWailsConfig(template []byte, version string) ([]byte, error) {
	if !stableVersionPattern.MatchString(version) {
		return nil, fmt.Errorf("application version %q must use Major.Minor.Patch", version)
	}
	var configuration map[string]any
	if err := json.Unmarshal(template, &configuration); err != nil {
		return nil, fmt.Errorf("parse Wails template: %w", err)
	}
	info, ok := configuration["info"].(map[string]any)
	if !ok {
		return nil, errors.New("Wails template is missing the info object")
	}
	if _, duplicated := info["productVersion"]; duplicated {
		return nil, errors.New("Wails template must not define productVersion; VERSION is authoritative")
	}
	info["productVersion"] = version
	rendered, err := json.MarshalIndent(configuration, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("render Wails configuration: %w", err)
	}
	return append(rendered, '\n'), nil
}

func generateWailsConfig(versionPath, templatePath, outputPath string) (string, error) {
	version, err := readVersion(versionPath)
	if err != nil {
		return "", err
	}
	template, err := os.ReadFile(templatePath)
	if err != nil {
		return "", fmt.Errorf("read Wails template: %w", err)
	}
	rendered, err := renderWailsConfig(template, version)
	if err != nil {
		return "", err
	}
	if current, readErr := os.ReadFile(outputPath); readErr == nil && string(current) == string(rendered) {
		return version, nil
	}
	directory := filepath.Dir(outputPath)
	temporary, err := os.CreateTemp(directory, ".wails-version-*")
	if err != nil {
		return "", fmt.Errorf("create temporary Wails configuration: %w", err)
	}
	temporaryPath := temporary.Name()
	defer os.Remove(temporaryPath)
	if _, err := temporary.Write(rendered); err != nil {
		_ = temporary.Close()
		return "", fmt.Errorf("write temporary Wails configuration: %w", err)
	}
	if err := temporary.Chmod(0o644); err != nil {
		_ = temporary.Close()
		return "", fmt.Errorf("set Wails configuration permissions: %w", err)
	}
	if err := temporary.Close(); err != nil {
		return "", fmt.Errorf("close temporary Wails configuration: %w", err)
	}
	if err := os.Rename(temporaryPath, outputPath); err != nil {
		// Windows cannot atomically replace an existing destination. The file is
		// generated and ignored, so remove only that exact destination and retry.
		if removeErr := os.Remove(outputPath); removeErr != nil && !os.IsNotExist(removeErr) {
			return "", fmt.Errorf("remove old Wails configuration: %w", removeErr)
		}
		if retryErr := os.Rename(temporaryPath, outputPath); retryErr != nil {
			return "", fmt.Errorf("publish Wails configuration: %w", retryErr)
		}
	}
	return version, nil
}

func main() {
	versionPath := flag.String("version-file", "VERSION", "canonical application version file")
	templatePath := flag.String("template", "wails.template.json", "tracked Wails configuration template")
	outputPath := flag.String("output", "wails.json", "generated Wails configuration")
	flag.Parse()

	version, err := generateWailsConfig(*versionPath, *templatePath, *outputPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("Prepared Wails build metadata for version %s.\n", version)
}
