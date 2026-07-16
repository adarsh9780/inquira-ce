package modelconfig

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

type HTTPDoer interface {
	Do(*http.Request) (*http.Response, error)
}

type providerClient struct {
	http HTTPDoer
}

func (c providerClient) verify(ctx context.Context, provider, key string) VerifyResponse {
	provider = normalizeProvider(provider)
	if provider == "ollama" {
		return VerifyResponse{Valid: true}
	}
	endpoint := "https://openrouter.ai/api/v1/auth/key"
	if provider == "openai" {
		endpoint = "https://api.openai.com/v1/models"
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return VerifyResponse{Error: "network_error"}
	}
	request.Header.Set("Authorization", "Bearer "+strings.TrimSpace(key))
	response, err := c.http.Do(request)
	if err != nil {
		return VerifyResponse{Error: "network_error"}
	}
	defer response.Body.Close()
	_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 4096))
	switch {
	case response.StatusCode >= 200 && response.StatusCode < 300:
		return VerifyResponse{Valid: true}
	case response.StatusCode == http.StatusTooManyRequests:
		return VerifyResponse{Error: "quota_exceeded"}
	case response.StatusCode == http.StatusUnauthorized || response.StatusCode == http.StatusForbidden:
		return VerifyResponse{Error: "invalid_key"}
	default:
		return VerifyResponse{Error: "network_error"}
	}
}

func (c providerClient) refresh(ctx context.Context, provider, key, baseURL string) (Catalog, string, string, error) {
	provider = normalizeProvider(provider)
	if provider == "ollama" {
		resolved := strings.TrimRight(strings.TrimSpace(baseURL), "/")
		if resolved == "" {
			resolved = "http://localhost:11434"
		}
		resolved = strings.TrimSuffix(resolved, "/v1")
		endpoint := resolved + "/api/tags"
		response, err := c.get(ctx, endpoint, "", "")
		if err != nil {
			return Catalog{}, "", "ollama_unreachable", fmt.Errorf("Ollama not detected at %q", resolved)
		}
		models := extractOllamaModels(response)
		catalog := buildRefreshedCatalog(provider, models)
		catalog.BaseURL = resolved
		return catalog, fmt.Sprintf("Refreshed %d Ollama models.", len(catalog.MainModels)), "", nil
	}

	if strings.TrimSpace(key) == "" {
		return Catalog{}, "", "missing_key", fmt.Errorf("API key is required to refresh %s models", provider)
	}
	endpoint := "https://openrouter.ai/api/v1/models/user"
	if provider == "openai" {
		endpoint = "https://api.openai.com/v1/models"
	}
	payload, status, err := c.getWithStatus(ctx, endpoint, "Authorization", "Bearer "+strings.TrimSpace(key))
	if err != nil {
		return Catalog{}, "", "refresh_failed", err
	}
	if provider == "openrouter" && status == http.StatusNotFound {
		payload, status, err = c.getWithStatus(ctx, "https://openrouter.ai/api/v1/models", "Authorization", "Bearer "+strings.TrimSpace(key))
		if err != nil {
			return Catalog{}, "", "refresh_failed", err
		}
	}
	if status < 200 || status >= 300 {
		return Catalog{}, "", "refresh_failed", fmt.Errorf("provider returned HTTP %d", status)
	}
	models := extractDataModels(payload)
	if provider == "openai" {
		models = filterOpenAIChatModels(models)
	}
	if len(models) == 0 {
		return Catalog{}, "", "refresh_failed", fmt.Errorf("provider returned no compatible models")
	}
	catalog := buildRefreshedCatalog(provider, models)
	if provider == "openrouter" {
		configured := true
		catalog.AccountModelsConfigured = &configured
		catalog.AccountModelsURL = "https://openrouter.ai/settings"
	}
	return catalog, fmt.Sprintf("Refreshed %d %s models.", len(catalog.MainModels), provider), "", nil
}

func (c providerClient) get(ctx context.Context, endpoint, header, value string) (map[string]any, error) {
	payload, status, err := c.getWithStatus(ctx, endpoint, header, value)
	if err != nil {
		return nil, err
	}
	if status < 200 || status >= 300 {
		return nil, fmt.Errorf("provider returned HTTP %d", status)
	}
	return payload, nil
}

func (c providerClient) getWithStatus(ctx context.Context, endpoint, header, value string) (map[string]any, int, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, 0, fmt.Errorf("create provider request: %w", err)
	}
	if header != "" {
		request.Header.Set(header, value)
	}
	response, err := c.http.Do(request)
	if err != nil {
		return nil, 0, fmt.Errorf("contact provider: %w", err)
	}
	defer response.Body.Close()
	decoder := json.NewDecoder(io.LimitReader(response.Body, 16<<20))
	var payload map[string]any
	if err := decoder.Decode(&payload); err != nil {
		if response.StatusCode >= 200 && response.StatusCode < 300 {
			return nil, response.StatusCode, fmt.Errorf("decode provider response: %w", err)
		}
		return map[string]any{}, response.StatusCode, nil
	}
	return payload, response.StatusCode, nil
}

func extractDataModels(payload map[string]any) []string {
	raw, _ := payload["data"].([]any)
	models := make([]string, 0, len(raw))
	for _, item := range raw {
		entry, _ := item.(map[string]any)
		if id, _ := entry["id"].(string); strings.TrimSpace(id) != "" {
			models = append(models, id)
		}
	}
	return unique(models)
}

func extractOllamaModels(payload map[string]any) []string {
	raw, _ := payload["models"].([]any)
	models := make([]string, 0, len(raw))
	for _, item := range raw {
		entry, _ := item.(map[string]any)
		id, _ := entry["model"].(string)
		if id == "" {
			id, _ = entry["name"].(string)
		}
		models = append(models, id)
	}
	return unique(models)
}

func filterOpenAIChatModels(models []string) []string {
	result := make([]string, 0, len(models))
	for _, model := range models {
		lower := strings.ToLower(model)
		blocked := false
		for _, token := range []string{"embedding", "whisper", "moderation", "tts", "transcribe", "gpt-image", "dall"} {
			if strings.Contains(lower, token) {
				blocked = true
				break
			}
		}
		if blocked {
			continue
		}
		if strings.HasPrefix(lower, "gpt") || strings.HasPrefix(lower, "o1") || strings.HasPrefix(lower, "o3") || strings.HasPrefix(lower, "o4") || strings.HasPrefix(lower, "chatgpt") {
			result = append(result, model)
		}
	}
	return unique(result)
}

func buildRefreshedCatalog(provider string, models []string) Catalog {
	models = unique(models)
	fallback := defaultCatalogs()[provider]
	if len(models) == 0 {
		return fallback
	}
	lite := make([]string, 0)
	for _, model := range models {
		lower := strings.ToLower(model)
		for _, hint := range []string{"nano", "mini", "haiku", "lite", "small", ":3b", ":2b", "flash-lite", "free"} {
			if strings.Contains(lower, hint) {
				lite = append(lite, model)
				break
			}
		}
	}
	if len(lite) == 0 {
		lite = []string{models[0]}
	}
	catalog := Catalog{
		MainModels: models, LiteModels: unique(lite), DefaultMainModel: models[0],
		Source: "refreshed",
	}
	catalog.DefaultLiteModel = catalog.LiteModels[0]
	catalog.Models = modelEntries(provider, catalog.MainModels, catalog.LiteModels, "extended")
	for index := range catalog.Models {
		if contains(fallback.MainModels, catalog.Models[index].ID) || contains(fallback.LiteModels, catalog.Models[index].ID) {
			catalog.Models[index].Tags = []string{"recommended"}
		}
	}
	return catalog
}

func isValidBaseURL(raw string) bool {
	parsed, err := url.Parse(raw)
	return err == nil && (parsed.Scheme == "http" || parsed.Scheme == "https") && parsed.Host != ""
}
