package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestNormalizeVersion(t *testing.T) {
	t.Parallel()

	for _, test := range []struct {
		input string
		want  string
	}{
		{input: "0.6.0", want: "0.6.0"},
		{input: "v1.2.3", want: "1.2.3"},
		{input: " v10.20.30 ", want: "10.20.30"},
	} {
		got, err := normalizeVersion(test.input)
		if err != nil {
			t.Fatalf("normalizeVersion(%q): %v", test.input, err)
		}
		if got != test.want {
			t.Fatalf("normalizeVersion(%q) = %q, want %q", test.input, got, test.want)
		}
	}
}

func TestNormalizeVersionRejectsUnsupportedValues(t *testing.T) {
	t.Parallel()

	for _, input := range []string{"", "0.6", "v0.6.0-beta.1", "release-1.0.0", "1.2.3.4"} {
		if _, err := normalizeVersion(input); err == nil {
			t.Fatalf("normalizeVersion(%q) unexpectedly succeeded", input)
		}
	}
}

func TestUpdateWailsVersionPreservesConfiguration(t *testing.T) {
	t.Parallel()

	configPath := filepath.Join(t.TempDir(), "wails.json")
	initial := `{
  "name": "inquira-go",
  "outputfilename": "inquira-go",
  "info": {
    "companyName": "Inquira",
    "productVersion": "0.5.35"
  }
}
`
	if err := os.WriteFile(configPath, []byte(initial), 0o640); err != nil {
		t.Fatal(err)
	}

	if err := updateWailsVersion(configPath, "v0.6.0"); err != nil {
		t.Fatalf("updateWailsVersion: %v", err)
	}

	content, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatal(err)
	}
	var configuration map[string]any
	if err := json.Unmarshal(content, &configuration); err != nil {
		t.Fatal(err)
	}

	if configuration["name"] != "inquira-go" || configuration["outputfilename"] != "inquira-go" {
		t.Fatalf("configuration fields were not preserved: %#v", configuration)
	}
	info, ok := configuration["info"].(map[string]any)
	if !ok {
		t.Fatalf("missing info object: %#v", configuration)
	}
	if info["companyName"] != "Inquira" || info["productVersion"] != "0.6.0" {
		t.Fatalf("unexpected info object: %#v", info)
	}

	fileInfo, err := os.Stat(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if fileInfo.Mode().Perm() != 0o640 {
		t.Fatalf("permissions = %o, want 640", fileInfo.Mode().Perm())
	}
}
