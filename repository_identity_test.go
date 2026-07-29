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
		".gitleaksignore": {
			"Historical CE Supabase publishable key",
			"Historical Google API key",
			"Revoked",
			"secret-scanning alert #1",
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
}
