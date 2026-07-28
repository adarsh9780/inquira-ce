package main

import (
	"archive/tar"
	"archive/zip"
	"compress/gzip"
	"crypto/sha256"
	"crypto/subtle"
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
	"time"

	"inquira-go/internal/runtimeprovision/contract"
)

const (
	defaultUVVersion  = "0.11.28"
	maxArchiveBytes   = 100 << 20
	maxExecutableSize = 100 << 20
)

// Values come from the immutable sha256.sum asset published with each Astral
// release at https://github.com/astral-sh/uv/releases.
var trustedUVArchiveSHA256 = map[string]map[string]string{
	"0.11.28": {
		"uv-aarch64-apple-darwin.tar.gz":      "33540eb7c883ab857eff79bd5ac2aa31fe27b595abecb4a9c003a2c998447232",
		"uv-aarch64-pc-windows-msvc.zip":      "3248109afad3ec59baad299d324ff53de17e2d9a3b3e21580ffd26744b11e036",
		"uv-aarch64-unknown-linux-gnu.tar.gz": "03e9fe0a81b0718d0bc84625de3885df6cc3f89a8b6af6121d6b9f6113fb6533",
		"uv-x86_64-apple-darwin.tar.gz":       "2ad79983127ffca7d77b77ce6a24278d7e4f7b817a1acf72fea5f8124b4aac5e",
		"uv-x86_64-pc-windows-msvc.zip":       "0a23463216d09c6a72ff80ef5dc5a795f07dc1575cb84d24596c2f124a441b7b",
		"uv-x86_64-unknown-linux-gnu.tar.gz":  "e490a6464492183c5d4534a5527fb4440f7f2bb2f228162ad7e4afe076dc0224",
	},
}

var downloadClient = &http.Client{Timeout: 5 * time.Minute}

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
	archiveName := fmt.Sprintf("uv-%s.%s", target, archiveType)
	expectedArchiveSHA256, err := archiveSHA256(version, archiveName)
	if err != nil {
		return err
	}
	url := fmt.Sprintf(
		"https://github.com/astral-sh/uv/releases/download/%s/%s",
		version,
		archiveName,
	)

	temporary, err := os.CreateTemp("", "inquira-uv-archive-*")
	if err != nil {
		return fmt.Errorf("create temporary archive: %w", err)
	}
	temporaryPath := temporary.Name()
	_ = temporary.Close()
	defer os.Remove(temporaryPath)

	archiveSize, err := download(url, temporaryPath, expectedArchiveSHA256)
	if err != nil {
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
	workerLockSHA256, err := fileSHA256(filepath.Join("python", "data_worker", "uv.lock"))
	if err != nil {
		return fmt.Errorf("fingerprint data worker lockfile: %w", err)
	}
	info := contract.BundleInfo{
		SchemaVersion:         contract.ManifestSchemaVersion,
		InquiraCompatibility:  contract.InquiraCompatibility,
		Version:               version,
		GOOS:                  goos,
		GOARCH:                goarch,
		File:                  executable,
		SHA256:                hex.EncodeToString(digest[:]),
		SourceURL:             url,
		ArchiveSHA256:         expectedArchiveSHA256,
		ArchiveSize:           archiveSize,
		PythonImplementation:  contract.PythonImplementation,
		PythonVersion:         contract.ManagedPythonVersion,
		PythonDistribution:    contract.PythonDistribution,
		WorkerProtocolVersion: contract.WorkerProtocolVersion,
		WorkerLockSHA256:      workerLockSHA256,
		Capabilities:          append([]string(nil), contract.RuntimeCapabilities...),
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

func archiveSHA256(version, archiveName string) (string, error) {
	release, ok := trustedUVArchiveSHA256[version]
	if !ok {
		return "", fmt.Errorf("UV %s is not trusted; add its published archive checksums before building", version)
	}
	digest, ok := release[archiveName]
	if !ok {
		return "", fmt.Errorf("UV %s archive %s has no trusted checksum", version, archiveName)
	}
	return digest, nil
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

func download(url, output, expectedSHA256 string) (int64, error) {
	expectedDigest, err := hex.DecodeString(expectedSHA256)
	if err != nil || len(expectedDigest) != sha256.Size {
		return 0, fmt.Errorf("trusted UV archive checksum is invalid")
	}
	response, err := downloadClient.Get(url) // #nosec G107 -- URL is constructed from a pinned, checksummed GitHub release.
	if err != nil {
		return 0, fmt.Errorf("download UV: %w", err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("download UV: %s returned %s", url, response.Status)
	}
	file, err := os.Create(output)
	if err != nil {
		return 0, fmt.Errorf("create UV archive: %w", err)
	}
	hasher := sha256.New()
	written, err := copyWithLimit(io.MultiWriter(file, hasher), response.Body, maxArchiveBytes)
	if err != nil {
		_ = file.Close()
		_ = os.Remove(output)
		return 0, fmt.Errorf("save UV archive: %w", err)
	}
	if err := file.Close(); err != nil {
		_ = os.Remove(output)
		return 0, fmt.Errorf("save UV archive: %w", err)
	}
	if written > maxArchiveBytes {
		_ = os.Remove(output)
		return 0, fmt.Errorf("download UV: archive exceeds %d bytes", maxArchiveBytes)
	}
	if subtle.ConstantTimeCompare(hasher.Sum(nil), expectedDigest) != 1 {
		_ = os.Remove(output)
		return 0, fmt.Errorf("download UV: archive checksum mismatch")
	}
	return written, nil
}

func fileSHA256(path string) (string, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(content)
	return hex.EncodeToString(digest[:]), nil
}

func copyWithLimit(destination io.Writer, source io.Reader, limit int64) (int64, error) {
	return io.Copy(destination, io.LimitReader(source, limit+1))
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
			if header.Size < 0 || header.Size > maxExecutableSize {
				return nil, fmt.Errorf("UV executable has invalid size %d", header.Size)
			}
			return readExecutable(tarReader)
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
			if item.UncompressedSize64 > maxExecutableSize {
				return nil, fmt.Errorf("UV executable exceeds %d bytes", maxExecutableSize)
			}
			reader, err := item.Open()
			if err != nil {
				return nil, err
			}
			defer reader.Close()
			return readExecutable(reader)
		}
	}
	return nil, fmt.Errorf("%s not found in UV archive", executable)
}

func readExecutable(reader io.Reader) ([]byte, error) {
	limited := io.LimitReader(reader, maxExecutableSize+1)
	payload, err := io.ReadAll(limited)
	if err != nil {
		return nil, err
	}
	if len(payload) > maxExecutableSize {
		return nil, fmt.Errorf("UV executable exceeds %d bytes", maxExecutableSize)
	}
	return payload, nil
}
