package main

import (
	"os"
	"regexp"
	"strings"
	"testing"
)

func TestBackendEmbedsCanonicalApplicationVersion(t *testing.T) {
	content, err := os.ReadFile("VERSION")
	if err != nil {
		t.Fatal(err)
	}
	want := strings.TrimSpace(string(content))
	if !regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(want) {
		t.Fatalf("VERSION = %q, want Major.Minor.Patch", want)
	}
	if got := applicationVersion(); got != want {
		t.Fatalf("applicationVersion() = %q, want %q", got, want)
	}
	if got := (&App{}).GetApplicationVersion(); got != want {
		t.Fatalf("GetApplicationVersion() = %q, want %q", got, want)
	}
}
