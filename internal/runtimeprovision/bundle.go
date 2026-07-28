package runtimeprovision

import (
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"slices"

	"inquira-go/internal/runtimeprovision/contract"
)

// The build preparation command writes the target-specific UV binary and
// manifest into assets before Go compiles the Wails executable.
//
//go:embed assets/*
var bundledAssets embed.FS

type BundleInfo = contract.BundleInfo

func loadBundleInfo(source fs.FS) (BundleInfo, error) {
	payload, err := fs.ReadFile(source, "assets/manifest.json")
	if err != nil {
		return BundleInfo{}, fmt.Errorf("UV bundle is not prepared: %w", err)
	}
	var info BundleInfo
	if err := json.Unmarshal(payload, &info); err != nil {
		return BundleInfo{}, fmt.Errorf("decode UV bundle manifest: %w", err)
	}
	if info.SchemaVersion != contract.ManifestSchemaVersion ||
		info.InquiraCompatibility != contract.InquiraCompatibility ||
		info.File == "" ||
		info.Version == "" ||
		info.SHA256 == "" ||
		info.SourceURL == "" ||
		info.ArchiveSHA256 == "" ||
		info.ArchiveSize <= 0 ||
		info.PythonImplementation != contract.PythonImplementation ||
		info.PythonVersion != contract.ManagedPythonVersion ||
		info.PythonDistribution != contract.PythonDistribution ||
		info.WorkerProtocolVersion != contract.WorkerProtocolVersion ||
		info.WorkerLockSHA256 == "" ||
		len(info.Capabilities) == 0 {
		return BundleInfo{}, fmt.Errorf("UV bundle manifest is incomplete")
	}
	for _, capability := range contract.RuntimeCapabilities {
		if !slices.Contains(info.Capabilities, capability) {
			return BundleInfo{}, fmt.Errorf("UV bundle manifest is missing required capability %q", capability)
		}
	}
	return info, nil
}

func extractBundle(source fs.FS, destination string) (string, BundleInfo, error) {
	info, err := loadBundleInfo(source)
	if err != nil {
		return "", BundleInfo{}, err
	}
	if info.GOOS != runtime.GOOS || info.GOARCH != runtime.GOARCH {
		return "", BundleInfo{}, fmt.Errorf(
			"UV bundle targets %s/%s, application runs on %s/%s",
			info.GOOS,
			info.GOARCH,
			runtime.GOOS,
			runtime.GOARCH,
		)
	}

	payload, err := fs.ReadFile(source, "assets/"+info.File)
	if err != nil {
		return "", BundleInfo{}, fmt.Errorf("read embedded UV binary: %w", err)
	}
	digest := sha256.Sum256(payload)
	if actual := hex.EncodeToString(digest[:]); actual != info.SHA256 {
		return "", BundleInfo{}, fmt.Errorf("embedded UV checksum mismatch")
	}

	if err := os.MkdirAll(destination, 0o700); err != nil {
		return "", BundleInfo{}, fmt.Errorf("create UV runtime directory: %w", err)
	}
	output := filepath.Join(destination, info.File)
	if existing, readErr := os.ReadFile(output); readErr == nil {
		existingDigest := sha256.Sum256(existing)
		if hex.EncodeToString(existingDigest[:]) == info.SHA256 {
			if err := os.Chmod(output, 0o700); err != nil {
				return "", BundleInfo{}, fmt.Errorf("make existing UV binary executable: %w", err)
			}
			return output, info, nil
		}
	}

	temporary := output + ".tmp"
	if err := os.WriteFile(temporary, payload, 0o700); err != nil {
		return "", BundleInfo{}, fmt.Errorf("write embedded UV binary: %w", err)
	}
	if err := os.Rename(temporary, output); err != nil {
		_ = os.Remove(temporary)
		return "", BundleInfo{}, fmt.Errorf("activate embedded UV binary: %w", err)
	}
	return output, info, nil
}
