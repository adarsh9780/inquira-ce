package main

import (
	"archive/tar"
	"archive/zip"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

const defaultUVVersion = "0.11.28"

type manifest struct {
	Version string `json:"version"`
	GOOS    string `json:"goos"`
	GOARCH  string `json:"goarch"`
	File    string `json:"file"`
	SHA256  string `json:"sha256"`
}

func main() {
	version := flag.String("version", defaultUVVersion, "UV release version")
	goos := flag.String("goos", runtime.GOOS, "target operating system")
	goarch := flag.String("goarch", runtime.GOARCH, "target architecture")
	output := flag.String("output", "internal/runtimeprovision/assets", "bundle asset directory")
	flag.Parse()

	if err := prepare(*version, *goos, *goarch, *output); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func prepare(version, goos, goarch, output string) error {
	target, archiveType, executable, err := targetDetails(goos, goarch)
	if err != nil {
		return err
	}
	url := fmt.Sprintf(
		"https://github.com/astral-sh/uv/releases/download/%s/uv-%s.%s",
		version,
		target,
		archiveType,
	)

	temporary, err := os.CreateTemp("", "inquira-uv-archive-*")
	if err != nil {
		return fmt.Errorf("create temporary archive: %w", err)
	}
	temporaryPath := temporary.Name()
	_ = temporary.Close()
	defer os.Remove(temporaryPath)

	if err := download(url, temporaryPath); err != nil {
		return err
	}
	payload, err := extractExecutable(temporaryPath, archiveType, executable)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(output, 0o755); err != nil {
		return fmt.Errorf("create asset directory: %w", err)
	}
	executablePath := filepath.Join(output, executable)
	if err := os.WriteFile(executablePath, payload, 0o755); err != nil {
		return fmt.Errorf("write UV executable: %w", err)
	}
	digest := sha256.Sum256(payload)
	info := manifest{
		Version: version,
		GOOS:    goos,
		GOARCH:  goarch,
		File:    executable,
		SHA256:  hex.EncodeToString(digest[:]),
	}
	encoded, err := json.MarshalIndent(info, "", "  ")
	if err != nil {
		return fmt.Errorf("encode manifest: %w", err)
	}
	encoded = append(encoded, '\n')
	if err := os.WriteFile(filepath.Join(output, "manifest.json"), encoded, 0o644); err != nil {
		return fmt.Errorf("write manifest: %w", err)
	}
	fmt.Printf("Prepared UV %s for %s/%s\n", version, goos, goarch)
	return nil
}

func targetDetails(goos, goarch string) (string, string, string, error) {
	architecture := map[string]string{"amd64": "x86_64", "arm64": "aarch64"}[goarch]
	if architecture == "" {
		return "", "", "", fmt.Errorf("unsupported UV architecture %q", goarch)
	}
	switch goos {
	case "darwin":
		return architecture + "-apple-darwin", "tar.gz", "uv", nil
	case "linux":
		return architecture + "-unknown-linux-gnu", "tar.gz", "uv", nil
	case "windows":
		return architecture + "-pc-windows-msvc", "zip", "uv.exe", nil
	default:
		return "", "", "", fmt.Errorf("unsupported UV operating system %q", goos)
	}
}

func download(url, output string) error {
	response, err := http.Get(url) // #nosec G107 -- URL is constructed from a pinned GitHub release.
	if err != nil {
		return fmt.Errorf("download UV: %w", err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("download UV: %s returned %s", url, response.Status)
	}
	file, err := os.Create(output)
	if err != nil {
		return fmt.Errorf("create UV archive: %w", err)
	}
	defer file.Close()
	if _, err := io.Copy(file, response.Body); err != nil {
		return fmt.Errorf("save UV archive: %w", err)
	}
	return nil
}

func extractExecutable(path, archiveType, executable string) ([]byte, error) {
	if archiveType == "zip" {
		return extractZip(path, executable)
	}
	return extractTarGz(path, executable)
}

func extractTarGz(path, executable string) ([]byte, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	gzipReader, err := gzip.NewReader(file)
	if err != nil {
		return nil, fmt.Errorf("open UV gzip archive: %w", err)
	}
	defer gzipReader.Close()
	tarReader := tar.NewReader(gzipReader)
	for {
		header, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read UV tar archive: %w", err)
		}
		if filepath.Base(header.Name) == executable {
			return io.ReadAll(tarReader)
		}
	}
	return nil, fmt.Errorf("%s not found in UV archive", executable)
}

func extractZip(path, executable string) ([]byte, error) {
	archive, err := zip.OpenReader(path)
	if err != nil {
		return nil, fmt.Errorf("open UV zip archive: %w", err)
	}
	defer archive.Close()
	for _, item := range archive.File {
		if strings.EqualFold(filepath.Base(item.Name), executable) {
			reader, err := item.Open()
			if err != nil {
				return nil, err
			}
			defer reader.Close()
			return io.ReadAll(reader)
		}
	}
	return nil, fmt.Errorf("%s not found in UV archive", executable)
}
