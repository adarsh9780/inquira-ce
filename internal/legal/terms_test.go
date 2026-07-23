package legal

import (
	"strings"
	"testing"
)

func TestCurrentTermsBundlesDesktopLegalDocument(t *testing.T) {
	terms := CurrentTerms()
	if terms.LastUpdated != "2026-06-07" {
		t.Fatalf("last updated = %q", terms.LastUpdated)
	}
	for _, section := range []string{"Main Risks", "Data Storage and Ownership", "Warranty Disclaimer", "Limitation of Liability"} {
		if !strings.Contains(terms.Markdown, section) {
			t.Fatalf("terms missing %q", section)
		}
	}
}
