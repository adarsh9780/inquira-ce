package legal

import (
	_ "embed"
	"strings"
)

//go:embed terms.md
var termsMarkdown string

type Terms struct {
	Markdown    string `json:"markdown"`
	LastUpdated string `json:"last_updated"`
}

func CurrentTerms() Terms {
	markdown := strings.TrimSpace(termsMarkdown)
	return Terms{Markdown: markdown, LastUpdated: extractLastUpdated(markdown)}
}

func extractLastUpdated(markdown string) string {
	for _, rawLine := range strings.Split(markdown, "\n") {
		line := strings.TrimSpace(rawLine)
		if strings.HasPrefix(strings.ToLower(line), "last updated:") {
			return strings.TrimSpace(strings.SplitN(line, ":", 2)[1])
		}
	}
	return ""
}
