package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"regexp"
	"strings"
)

var stableVersionPattern = regexp.MustCompile(`^\d+\.\d+\.\d+$`)

func normalizeVersion(raw string) (string, error) {
	version := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(raw), "v"))
	if !stableVersionPattern.MatchString(version) {
		return "", fmt.Errorf("release version %q must use Major.Minor.Patch, for example 0.6.0", raw)
	}
	return version, nil
}

func updateWailsVersion(path, rawVersion string) error {
	version, err := normalizeVersion(rawVersion)
	if err != nil {
		return err
	}

	content, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read Wails configuration: %w", err)
	}

	var configuration map[string]any
	if err := json.Unmarshal(content, &configuration); err != nil {
		return fmt.Errorf("parse Wails configuration: %w", err)
	}

	info, ok := configuration["info"].(map[string]any)
	if !ok {
		return errors.New("Wails configuration is missing the info object")
	}
	info["productVersion"] = version

	rendered, err := json.MarshalIndent(configuration, "", "  ")
	if err != nil {
		return fmt.Errorf("render Wails configuration: %w", err)
	}
	rendered = append(rendered, '\n')

	fileInfo, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("inspect Wails configuration: %w", err)
	}
	if err := os.WriteFile(path, rendered, fileInfo.Mode().Perm()); err != nil {
		return fmt.Errorf("write Wails configuration: %w", err)
	}
	return nil
}

func main() {
	version := flag.String("version", "", "release version, with or without a leading v")
	configPath := flag.String("config", "wails.json", "path to the Wails configuration")
	flag.Parse()

	if err := updateWailsVersion(*configPath, *version); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	normalized, _ := normalizeVersion(*version)
	fmt.Printf("Prepared Wails build metadata for version %s.\n", normalized)
}
