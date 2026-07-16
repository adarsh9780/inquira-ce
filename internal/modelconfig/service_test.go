package modelconfig

import (
	"context"
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

func response(status int, body string) *http.Response {
	return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}
}
