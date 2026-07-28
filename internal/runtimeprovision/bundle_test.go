package runtimeprovision

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"testing/fstest"

	"inquira-go/internal/runtimeprovision/contract"
)

func TestExtractBundleValidatesAndWritesExecutable(t *testing.T) {
	source := testBundleFS(t)
	info, err := loadBundleInfo(source)
	if err != nil {
		t.Fatal(err)
	}

	output, extracted, err := extractBundle(source, t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(extracted, info) {
		t.Fatalf("unexpected manifest: %#v", extracted)
	}
	written, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	if string(written) != "test UV payload" {
		t.Fatalf("unexpected extracted payload %q", written)
	}
	if filepath.Base(output) != info.File {
		t.Fatalf("unexpected output path %q", output)
	}
}

func testBundleFS(t *testing.T, workerLockSHA256 ...string) fstest.MapFS {
	t.Helper()
	payload := []byte("test UV payload")
	digest := sha256.Sum256(payload)
	lockDigest := strings.Repeat("b", sha256.Size*2)
	if len(workerLockSHA256) > 0 {
		lockDigest = workerLockSHA256[0]
	}
	info := BundleInfo{
		SchemaVersion:         contract.ManifestSchemaVersion,
		InquiraCompatibility:  contract.InquiraCompatibility,
		Version:               "test",
		GOOS:                  runtime.GOOS,
		GOARCH:                runtime.GOARCH,
		File:                  executableName("uv"),
		SHA256:                hex.EncodeToString(digest[:]),
		SourceURL:             "https://example.test/uv",
		ArchiveSHA256:         strings.Repeat("a", sha256.Size*2),
		ArchiveSize:           int64(len(payload)),
		PythonImplementation:  contract.PythonImplementation,
		PythonVersion:         contract.ManagedPythonVersion,
		PythonDistribution:    contract.PythonDistribution,
		WorkerProtocolVersion: contract.WorkerProtocolVersion,
		WorkerLockSHA256:      lockDigest,
		Capabilities:          append([]string(nil), contract.RuntimeCapabilities...),
	}
	manifest, err := json.Marshal(info)
	if err != nil {
		t.Fatal(err)
	}
	return fstest.MapFS{
		"assets/manifest.json": {Data: manifest},
		"assets/" + info.File:  {Data: payload},
	}
}

func TestLoadBundleInfoRejectsMissingRuntimeCapability(t *testing.T) {
	source := testBundleFS(t)
	var info BundleInfo
	if err := json.Unmarshal(source["assets/manifest.json"].Data, &info); err != nil {
		t.Fatal(err)
	}
	info.Capabilities = info.Capabilities[1:]
	manifest, err := json.Marshal(info)
	if err != nil {
		t.Fatal(err)
	}
	source["assets/manifest.json"] = &fstest.MapFile{Data: manifest}

	if _, err := loadBundleInfo(source); err == nil || !strings.Contains(err.Error(), "missing required capability") {
		t.Fatalf("missing capability error = %v", err)
	}
}

func TestExtractBundleRejectsChecksumMismatch(t *testing.T) {
	info := BundleInfo{
		SchemaVersion:         contract.ManifestSchemaVersion,
		InquiraCompatibility:  contract.InquiraCompatibility,
		Version:               "test",
		GOOS:                  runtime.GOOS,
		GOARCH:                runtime.GOARCH,
		File:                  executableName("uv"),
		SHA256:                "invalid",
		SourceURL:             "https://example.test/uv",
		ArchiveSHA256:         strings.Repeat("a", sha256.Size*2),
		ArchiveSize:           7,
		PythonImplementation:  contract.PythonImplementation,
		PythonVersion:         contract.ManagedPythonVersion,
		PythonDistribution:    contract.PythonDistribution,
		WorkerProtocolVersion: contract.WorkerProtocolVersion,
		WorkerLockSHA256:      strings.Repeat("b", sha256.Size*2),
		Capabilities:          append([]string(nil), contract.RuntimeCapabilities...),
	}
	manifest, err := json.Marshal(info)
	if err != nil {
		t.Fatal(err)
	}
	source := fstest.MapFS{
		"assets/manifest.json": {Data: manifest},
		"assets/" + info.File:  {Data: []byte("payload")},
	}
	if _, _, err := extractBundle(source, t.TempDir()); err == nil {
		t.Fatal("expected checksum mismatch to fail")
	}
}
