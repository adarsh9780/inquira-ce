package main

import (
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestTargetDetails(t *testing.T) {
	tests := []struct {
		goos       string
		goarch     string
		target     string
		archive    string
		executable string
	}{
		{goos: "darwin", goarch: "arm64", target: "aarch64-apple-darwin", archive: "tar.gz", executable: "uv"},
		{goos: "linux", goarch: "amd64", target: "x86_64-unknown-linux-gnu", archive: "tar.gz", executable: "uv"},
		{goos: "windows", goarch: "amd64", target: "x86_64-pc-windows-msvc", archive: "zip", executable: "uv.exe"},
	}
	for _, test := range tests {
		t.Run(test.goos+"-"+test.goarch, func(t *testing.T) {
			target, archive, executable, err := targetDetails(test.goos, test.goarch)
			if err != nil {
				t.Fatal(err)
			}
			if target != test.target || archive != test.archive || executable != test.executable {
				t.Fatalf("got %q %q %q", target, archive, executable)
			}
		})
	}
}

func TestTargetDetailsRejectsUnsupportedTarget(t *testing.T) {
	if _, _, _, err := targetDetails("plan9", "amd64"); err == nil {
		t.Fatal("expected unsupported target to fail")
	}
}

func TestEverySupportedTargetHasTrustedArchiveChecksum(t *testing.T) {
	for _, goos := range []string{"darwin", "linux", "windows"} {
		for _, goarch := range []string{"amd64", "arm64"} {
			target, archiveType, _, err := targetDetails(goos, goarch)
			if err != nil {
				t.Fatal(err)
			}
			archiveName := "uv-" + target + "." + archiveType
			digest, err := archiveSHA256(defaultUVVersion, archiveName)
			if err != nil {
				t.Fatalf("%s/%s: %v", goos, goarch, err)
			}
			if len(digest) != sha256.Size*2 {
				t.Fatalf("%s/%s: invalid SHA-256 length %d", goos, goarch, len(digest))
			}
		}
	}
}

func TestArchiveSHA256RejectsUntrustedVersion(t *testing.T) {
	if _, err := archiveSHA256("99.0.0", "uv-aarch64-apple-darwin.tar.gz"); err == nil {
		t.Fatal("expected untrusted UV version to fail")
	}
}

func TestDownloadVerifiesArchiveChecksum(t *testing.T) {
	payload := []byte("trusted UV archive")
	digest := sha256.Sum256(payload)
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		_, _ = writer.Write(payload)
	}))
	t.Cleanup(server.Close)

	output := filepath.Join(t.TempDir(), "uv.tar.gz")
	size, err := download(server.URL, output, hex.EncodeToString(digest[:]))
	if err != nil {
		t.Fatal(err)
	}
	if size != int64(len(payload)) {
		t.Fatalf("downloaded %d bytes, want %d", size, len(payload))
	}
	actual, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	if string(actual) != string(payload) {
		t.Fatalf("downloaded %q, want %q", actual, payload)
	}
}

func TestDownloadRejectsArchiveChecksumMismatch(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		_, _ = writer.Write([]byte("untrusted archive"))
	}))
	t.Cleanup(server.Close)

	output := filepath.Join(t.TempDir(), "uv.tar.gz")
	wrongDigest := sha256.Sum256([]byte("different archive"))
	if _, err := download(server.URL, output, hex.EncodeToString(wrongDigest[:])); err == nil {
		t.Fatal("expected checksum mismatch to fail")
	}
	if _, err := os.Stat(output); !os.IsNotExist(err) {
		t.Fatalf("untrusted archive was not removed: %v", err)
	}
}
