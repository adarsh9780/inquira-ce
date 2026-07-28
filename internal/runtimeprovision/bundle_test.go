package runtimeprovision

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
	"testing/fstest"
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
	if extracted != info {
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

func testBundleFS(t *testing.T) fstest.MapFS {
	t.Helper()
	payload := []byte("test UV payload")
	digest := sha256.Sum256(payload)
	info := BundleInfo{
		Version: "test",
		GOOS:    runtime.GOOS,
		GOARCH:  runtime.GOARCH,
		File:    executableName("uv"),
		SHA256:  hex.EncodeToString(digest[:]),
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

func TestExtractBundleRejectsChecksumMismatch(t *testing.T) {
	info := BundleInfo{
		Version: "test",
		GOOS:    runtime.GOOS,
		GOARCH:  runtime.GOARCH,
		File:    executableName("uv"),
		SHA256:  "invalid",
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
