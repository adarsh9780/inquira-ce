package modelconfig

import (
	"strings"
)

var supportedProviders = []string{"openrouter", "openai", "ollama"}

func normalizeProvider(provider string) string {
	switch strings.ToLower(strings.TrimSpace(provider)) {
	case "openai":
		return "openai"
	case "ollama":
		return "ollama"
	case "api", "openrouter":
		return "openrouter"
	default:
		return "openrouter"
	}
}

func defaultCatalogs() map[string]Catalog {
	return map[string]Catalog{
		"openrouter": newDefaultCatalog("openrouter",
			[]string{"google/gemini-2.5-flash", "openai/gpt-4o", "anthropic/claude-sonnet-4-5"},
			[]string{"google/gemini-2.5-flash-lite"},
		),
		"openai": newDefaultCatalog("openai",
			[]string{"gpt-4.1", "gpt-4o"},
			[]string{"gpt-4.1-mini", "gpt-4o-mini"},
		),
		"ollama": withBaseURL(newDefaultCatalog("ollama",
			[]string{"llama3.2", "qwen2.5-coder:7b", "mistral", "deepseek-r1:8b"},
			[]string{"llama3.2:3b", "qwen2.5:3b", "gemma2:2b", "gemma2:9b"},
		), "http://localhost:11434"),
	}
}

func newDefaultCatalog(provider string, main, lite []string) Catalog {
	models := make([]ModelEntry, 0, len(main)+len(lite))
	seen := map[string]bool{}
	for _, id := range append(append([]string{}, main...), lite...) {
		if seen[id] {
			continue
		}
		seen[id] = true
		recommended := []string{"main"}
		if contains(lite, id) && contains(main, id) {
			recommended = []string{"both"}
		} else if contains(lite, id) {
			recommended = []string{"lite"}
		}
		models = append(models, ModelEntry{
			ID: id, DisplayName: displayName(id), Provider: provider,
			RecommendedFor: recommended, Tags: []string{"recommended"},
		})
	}
	return Catalog{
		MainModels: main, LiteModels: lite,
		DefaultMainModel: first(main), DefaultLiteModel: first(lite),
		Source: "default", Models: models,
	}
}

func withBaseURL(catalog Catalog, baseURL string) Catalog {
	catalog.BaseURL = baseURL
	return catalog
}

func mergeCatalogs(saved map[string]Catalog) map[string]Catalog {
	merged := defaultCatalogs()
	for _, provider := range supportedProviders {
		override, ok := saved[provider]
		if !ok || len(override.MainModels) == 0 {
			continue
		}
		if len(override.LiteModels) == 0 {
			override.LiteModels = []string{override.MainModels[0]}
		}
		if !contains(override.MainModels, override.DefaultMainModel) {
			override.DefaultMainModel = override.MainModels[0]
		}
		if !contains(override.LiteModels, override.DefaultLiteModel) {
			override.DefaultLiteModel = override.LiteModels[0]
		}
		if len(override.Models) == 0 {
			override.Models = modelEntries(provider, override.MainModels, override.LiteModels, "extended")
		}
		if provider == "ollama" && strings.TrimSpace(override.BaseURL) == "" {
			override.BaseURL = "http://localhost:11434"
		}
		merged[provider] = override
	}
	return merged
}

func modelEntries(provider string, main, lite []string, tag string) []ModelEntry {
	ids := unique(append(append([]string{}, main...), lite...))
	entries := make([]ModelEntry, 0, len(ids))
	for _, id := range ids {
		recommended := []string{"main"}
		if contains(main, id) && contains(lite, id) {
			recommended = []string{"both"}
		} else if contains(lite, id) {
			recommended = []string{"lite"}
		}
		entries = append(entries, ModelEntry{
			ID: id, DisplayName: displayName(id), Provider: provider,
			RecommendedFor: recommended, Tags: []string{tag},
		})
	}
	return entries
}

func displayName(id string) string {
	value := id
	if slash := strings.LastIndex(value, "/"); slash >= 0 {
		value = value[slash+1:]
	}
	words := strings.FieldsFunc(value, func(r rune) bool { return r == '-' || r == '_' })
	for index, word := range words {
		if word != "" {
			words[index] = strings.ToUpper(word[:1]) + word[1:]
		}
	}
	return strings.Join(words, " ")
}

func displayMainModels(provider string, catalog Catalog, selected string) []string {
	models := catalog.MainModels
	if provider == "openrouter" {
		models = nil
		for _, id := range catalog.MainModels {
			lower := strings.ToLower(id)
			if strings.HasPrefix(lower, "google/") || strings.HasPrefix(lower, "openai/") || strings.HasPrefix(lower, "anthropic/") {
				models = append(models, id)
			}
		}
	}
	models = unique(models)
	if len(models) > 100 {
		models = models[:100]
	}
	if selected != "" && contains(catalog.MainModels, selected) && !contains(models, selected) {
		models = append([]string{selected}, models...)
		if len(models) > 100 {
			models = models[:100]
		}
	}
	return models
}

func unique(values []string) []string {
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		result = append(result, value)
	}
	return result
}

func contains(values []string, candidate string) bool {
	for _, value := range values {
		if value == candidate {
			return true
		}
	}
	return false
}

func first(values []string) string {
	if len(values) == 0 {
		return ""
	}
	return values[0]
}
