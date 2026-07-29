package main

import (
	"os"
	"strings"
	"testing"
)

func TestCommunityEditionRepositoryIdentity(t *testing.T) {
	t.Parallel()

	requiredContent := map[string][]string{
		"go.mod": {
			"module github.com/adarsh9780/inquira-ce",
		},
		"README.md": {
			"# Inquira Community Edition",
			"## Product lineage",
			"September 2, 2025",
			"docs/project-history.md",
			"Sustainable Use",
			"License 1.0",
		},
		"docs/project-history.md": {
			"original Inquira CE repository was initialized on September 2, 2025",
			"two-parent",
			"No legacy commits were rebased, squashed, or assigned artificial dates",
		},
		"LICENSE": {
			"# Sustainable Use License",
			"Version 1.0",
		},
		"Makefile": {
			"REPOSITORY_NAME := inquira-ce",
			"GITHUB_REPOSITORY ?= $(GITHUB_OWNER)/$(REPOSITORY_NAME)",
			"VISIBILITY ?= public",
		},
		"docs/release-management.md": {
			"Inquira Community Edition uses GitHub Releases",
			"public GitHub Release assets",
		},
		".gitleaksignore": {
			"Historical CE Supabase publishable key",
			"Historical Google API key",
			"Revoked",
			"secret-scanning alert #1",
		},
	}

	prohibitedContent := map[string][]string{
		"README.md": {
			"private GitHub Release",
		},
		"docs/release-management.md": {
			"source repository is private",
			"private GitHub Release",
		},
	}

	for path, fragments := range requiredContent {
		path := path
		fragments := fragments
		t.Run(path, func(t *testing.T) {
			content, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("read %s: %v", path, err)
			}
			for _, fragment := range fragments {
				if !strings.Contains(string(content), fragment) {
					t.Errorf("%s does not contain %q", path, fragment)
				}
			}
		})
	}

	for path, fragments := range prohibitedContent {
		path := path
		fragments := fragments
		t.Run(path+"-prohibited", func(t *testing.T) {
			content, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("read %s: %v", path, err)
			}
			for _, fragment := range fragments {
				if strings.Contains(string(content), fragment) {
					t.Errorf("%s still contains obsolete identity text %q", path, fragment)
				}
			}
		})
	}
}
