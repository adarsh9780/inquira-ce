package desktop

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

func TestPrepareExportValidatesAndDecodesTheDesktopContract(t *testing.T) {
	payload := []byte{0, 1, 2, 255}
	prepared, err := PrepareExport(ExportRequest{
		DefaultFileName: "report.csv",
		ContentBase64:   base64.StdEncoding.EncodeToString(payload),
		Filters:         []ExportFilter{{Name: "CSV File", Extensions: []string{"csv", "CSV"}}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if prepared.DefaultFileName != "report.csv" || !slices.Equal(prepared.Content, payload) {
		t.Fatalf("prepared export = %#v", prepared)
	}
	if len(prepared.Filters) != 1 || !slices.Equal(prepared.Filters[0].Extensions, []string{"csv"}) {
		t.Fatalf("prepared filters = %#v", prepared.Filters)
	}
}

func TestPrepareExportRejectsUnsafeNamesFiltersAndPayloads(t *testing.T) {
	validPayload := base64.StdEncoding.EncodeToString([]byte("data"))
	for _, request := range []ExportRequest{
		{DefaultFileName: "", ContentBase64: validPayload},
		{DefaultFileName: "../report.csv", ContentBase64: validPayload},
		{DefaultFileName: "folder/report.csv", ContentBase64: validPayload},
		{DefaultFileName: "report\x00.csv", ContentBase64: validPayload},
		{DefaultFileName: "report.csv", ContentBase64: "not-base64"},
		{DefaultFileName: "report.csv", ContentBase64: validPayload, Filters: []ExportFilter{{Name: "Unsafe\nfilter", Extensions: []string{"csv"}}}},
		{DefaultFileName: "report.csv", ContentBase64: validPayload, Filters: []ExportFilter{{Name: "CSV", Extensions: []string{"../csv"}}}},
	} {
		if _, err := PrepareExport(request); err == nil {
			t.Fatalf("unsafe request unexpectedly succeeded: %#v", request)
		}
	}
}

func TestWriteExportAtomicallyReplacesTheSelectedFile(t *testing.T) {
	directory := t.TempDir()
	target := filepath.Join(directory, "report.csv")
	if err := os.WriteFile(target, []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := WriteExport(target, []byte("new contents")); err != nil {
		t.Fatal(err)
	}
	contents, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(contents) != "new contents" {
		t.Fatalf("export contents = %q", contents)
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 || strings.Contains(entries[0].Name(), ".tmp-") {
		t.Fatalf("export directory entries = %#v", entries)
	}
	info, err := os.Stat(target)
	if err != nil || info.Mode().Perm()&0o077 != 0 {
		t.Fatalf("export permissions = %#o, %v", info.Mode().Perm(), err)
	}
}

func TestWriteExportRejectsMissingDestinationsWithoutCreatingDirectories(t *testing.T) {
	missingParent := filepath.Join(t.TempDir(), "missing")
	if err := WriteExport(filepath.Join(missingParent, "report.csv"), []byte("data")); err == nil {
		t.Fatal("export with a missing parent unexpectedly succeeded")
	}
	if _, err := os.Stat(missingParent); !os.IsNotExist(err) {
		t.Fatalf("missing parent was created: %v", err)
	}
}
