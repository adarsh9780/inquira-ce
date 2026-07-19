package modelconfig

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

type memorySecrets struct {
	mu     sync.Mutex
	values map[string]string
}

func (s *memorySecrets) Set(provider, secret string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.values[normalizeProvider(provider)] = secret
	return nil
}
func (s *memorySecrets) Get(provider string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.values[normalizeProvider(provider)], nil
}
func (s *memorySecrets) Delete(provider string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.values, normalizeProvider(provider))
	return nil
}
func (s *memorySecrets) Has(provider string) (bool, error) {
	value, _ := s.Get(provider)
	return value != "", nil
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (fn roundTripFunc) Do(request *http.Request) (*http.Response, error) { return fn(request) }

func TestSaveConfigurationVerifiesKeyStoresSecretAndPersistsCatalog(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{}}
	httpClient := roundTripFunc(func(request *http.Request) (*http.Response, error) {
		if request.Header.Get("Authorization") != "Bearer test-secret" {
			t.Fatalf("authorization header was not set")
		}
		body := `{}`
		if strings.HasSuffix(request.URL.Path, "/models/user") {
			body = `{"data":[{"id":"google/gemini-2.5-flash"},{"id":"openai/gpt-4o-mini"}]}`
		}
		return response(http.StatusOK, body), nil
	})
	service := NewService(repository, secrets, httpClient)
	defer service.Close()

	key := "test-secret"
	provider := "openrouter"
	result, err := service.SaveConfiguration(context.Background(), SaveRequest{Provider: provider, APIKey: &key})
	if err != nil {
		t.Fatalf("SaveConfiguration() error = %v", err)
	}
	if result.Warning != "" || !result.SelectedProviderAPIKeyPresent {
		t.Fatalf("unexpected result: %#v", result)
	}
	stored, _ := secrets.Get(provider)
	if stored != key {
		t.Fatalf("stored key = %q", stored)
	}
	if !contains(result.ProviderModelCatalogs[provider].MainModels, "openai/gpt-4o-mini") {
		t.Fatalf("refreshed catalog = %#v", result.ProviderModelCatalogs[provider])
	}
}

func TestSaveConfigurationKeepsCredentialWhenCatalogRefreshFails(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{}}
	call := 0
	httpClient := roundTripFunc(func(request *http.Request) (*http.Response, error) {
		call++
		if call == 1 {
			return response(http.StatusOK, `{}`), nil
		}
		return response(http.StatusBadGateway, `{}`), nil
	})
	service := NewService(repository, secrets, httpClient)
	defer service.Close()

	key := "test-secret"
	result, err := service.SaveConfiguration(context.Background(), SaveRequest{Provider: "openrouter", APIKey: &key})
	if err != nil {
		t.Fatalf("SaveConfiguration() error = %v", err)
	}
	if result.Warning == "" {
		t.Fatal("expected cached catalog warning")
	}
	stored, _ := secrets.Get("openrouter")
	if stored != key {
		t.Fatal("verified credential was not retained")
	}
}

func TestVerifyAndDeleteAPIKey(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{"openai": "saved"}}
	service := NewService(repository, secrets, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return response(http.StatusUnauthorized, `{}`), nil
	}))
	defer service.Close()

	verification, err := service.VerifyKey(context.Background(), "openai", "wrong")
	if err != nil {
		t.Fatal(err)
	}
	if verification.Valid || verification.Error != "invalid_key" {
		t.Fatalf("verification = %#v", verification)
	}
	if _, err := service.DeleteKey(context.Background(), "openai"); err != nil {
		t.Fatal(err)
	}
	if has, _ := secrets.Has("openai"); has {
		t.Fatal("key was not deleted")
	}
}

func TestAnthropicConfigurationUsesNativeHeadersAndRuntime(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{}}
	httpClient := roundTripFunc(func(request *http.Request) (*http.Response, error) {
		if request.URL.String() != "https://api.anthropic.com/v1/models" ||
			request.Header.Get("x-api-key") != "anthropic-secret" || request.Header.Get("anthropic-version") != "2023-06-01" ||
			request.Header.Get("Authorization") != "" {
			t.Fatalf("unexpected Anthropic request: %s headers=%#v", request.URL, request.Header)
		}
		return response(http.StatusOK, `{"data":[{"id":"claude-sonnet-4-5"},{"id":"not-a-chat-model"}]}`), nil
	})
	service := NewService(repository, secrets, httpClient)
	defer service.Close()

	key := "anthropic-secret"
	provider := "anthropic"
	result, err := service.SaveConfiguration(context.Background(), SaveRequest{Provider: provider, APIKey: &key})
	if err != nil {
		t.Fatal(err)
	}
	if !contains(result.AvailableProviders, provider) || !contains(result.ProviderModelCatalogs[provider].MainModels, "claude-sonnet-4-5") ||
		contains(result.ProviderModelCatalogs[provider].MainModels, "not-a-chat-model") {
		t.Fatalf("Anthropic preferences = %#v", result)
	}
	runtimeConfig, err := service.RuntimeConfiguration(context.Background())
	if err != nil || runtimeConfig.Provider != provider || runtimeConfig.APIKey != key || runtimeConfig.BaseURL != "" {
		t.Fatalf("Anthropic runtime = %#v, %v", runtimeConfig, err)
	}
}

func TestUpdatePreferencesRejectsUnsafeValues(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository, &memorySecrets{values: map[string]string{}}, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return response(http.StatusOK, `{}`), nil
	}))
	defer service.Close()

	temperature := 3.0
	if _, err := service.UpdatePreferences(context.Background(), UpdateRequest{LLMTemperature: &temperature}); err == nil {
		t.Fatal("expected temperature validation error")
	}
}

func TestModelOnboardingRequiresAReadyConnectionAndPersistsCompletion(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{}}
	service := NewService(repository, secrets, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return response(http.StatusOK, `{}`), nil
	}))
	defer service.Close()

	status, err := service.GetOnboardingStatus(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if status.Completed || status.ConnectionReady || status.Provider != "openrouter" {
		t.Fatalf("fresh onboarding status = %#v", status)
	}
	if _, err := service.CompleteOnboarding(context.Background()); err == nil {
		t.Fatal("expected completion to require a model connection")
	}
	if err := secrets.Set("openrouter", "saved-secret"); err != nil {
		t.Fatal(err)
	}
	status, err = service.CompleteOnboarding(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !status.Completed || !status.ConnectionReady {
		t.Fatalf("completed onboarding status = %#v", status)
	}
	reloaded, err := repository.Load(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !reloaded.ModelOnboardingCompleted {
		t.Fatal("onboarding completion was not persisted")
	}
}

func TestOllamaOnboardingRequiresSuccessfulModelRefresh(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository, &memorySecrets{values: map[string]string{}}, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return response(http.StatusOK, `{}`), nil
	}))
	defer service.Close()

	preferences, err := repository.Load(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	preferences.LLMProvider = "ollama"
	if err := repository.Save(context.Background(), preferences); err != nil {
		t.Fatal(err)
	}
	status, err := service.GetOnboardingStatus(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if status.ConnectionReady {
		t.Fatal("default Ollama catalog must not count as a tested connection")
	}
	catalog := preferences.Catalogs["ollama"]
	catalog.Source = "refreshed"
	preferences.Catalogs["ollama"] = catalog
	if err := repository.Save(context.Background(), preferences); err != nil {
		t.Fatal(err)
	}
	status, err = service.GetOnboardingStatus(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !status.ConnectionReady {
		t.Fatal("refreshed Ollama catalog should mark the connection ready")
	}
}

func TestRefreshErrorDoesNotExposeTransportDetails(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{"openrouter": "saved-secret"}}
	service := NewService(repository, secrets, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return nil, errors.New("proxy password: very-sensitive")
	}))
	defer service.Close()

	_, err = service.RefreshModels(context.Background(), RefreshRequest{Provider: "openrouter"})
	if err == nil {
		t.Fatal("expected refresh error")
	}
	if strings.Contains(err.Error(), "very-sensitive") {
		t.Fatalf("transport details leaked across UI boundary: %v", err)
	}
}

func TestRuntimeConfigurationReadsSelectedModelAndKeyWithoutExposingItInPreferences(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{"openai": "runtime-secret"}}
	service := NewService(repository, secrets, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return response(http.StatusOK, `{}`), nil
	}))
	defer service.Close()
	provider := "openai"
	model, liteModel, codingModel := "gpt-4o", "gpt-4.1-mini", "gpt-4.1"
	if _, err := service.UpdatePreferences(context.Background(), UpdateRequest{
		LLMProvider: &provider, SelectedModel: &model, SelectedLiteModel: &liteModel, SelectedCodingModel: &codingModel,
	}); err != nil {
		t.Fatal(err)
	}
	runtimeConfig, err := service.RuntimeConfiguration(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if runtimeConfig.Provider != "openai" || runtimeConfig.Model != model || runtimeConfig.LiteModel != liteModel ||
		runtimeConfig.CodingModel != codingModel || runtimeConfig.APIKey != "runtime-secret" {
		t.Fatalf("runtime configuration = %#v", runtimeConfig)
	}
	preferences, err := service.GetPreferences(context.Background(), "openai")
	if err != nil {
		t.Fatal(err)
	}
	encoded, _ := json.Marshal(preferences)
	if strings.Contains(string(encoded), "runtime-secret") {
		t.Fatalf("preferences leaked runtime key: %s", encoded)
	}
}

func TestSchemaRuntimeConfigurationUsesLiteModelWithMainModelFallback(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	secrets := &memorySecrets{values: map[string]string{"openai": "runtime-secret"}}
	service := NewService(repository, secrets, roundTripFunc(func(*http.Request) (*http.Response, error) {
		return response(http.StatusOK, `{}`), nil
	}))
	defer service.Close()
	provider, mainModel, liteModel := "openai", "gpt-main", "gpt-lite"
	preferences, err := repository.Load(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	preferences.Catalogs[provider] = Catalog{
		MainModels: []string{mainModel}, LiteModels: []string{liteModel},
		DefaultMainModel: mainModel, DefaultLiteModel: liteModel,
	}
	if err := repository.Save(context.Background(), preferences); err != nil {
		t.Fatal(err)
	}
	maxTokens := 10000
	if _, err := service.UpdatePreferences(context.Background(), UpdateRequest{
		LLMProvider: &provider, SelectedModel: &mainModel, SelectedLiteModel: &liteModel, LLMMaxTokens: &maxTokens,
	}); err != nil {
		t.Fatal(err)
	}
	config, err := service.SchemaRuntimeConfiguration(context.Background())
	if err != nil || config.Model != liteModel || config.APIKey != "runtime-secret" || config.MaxTokens != 4096 {
		t.Fatalf("schema runtime configuration = %#v, %v", config, err)
	}
	preferences, err = repository.Load(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	preferences.SelectedLiteModel = ""
	preferences.Catalogs["openai"] = Catalog{}
	if err := repository.Save(context.Background(), preferences); err != nil {
		t.Fatal(err)
	}
	config, err = service.SchemaRuntimeConfiguration(context.Background())
	if err != nil || config.Model != mainModel {
		t.Fatalf("schema runtime fallback = %#v, %v", config, err)
	}
}

func response(status int, body string) *http.Response {
	return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}
}
