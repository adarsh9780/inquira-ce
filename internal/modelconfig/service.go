package modelconfig

import (
	"context"
	"fmt"
	"strings"
	"sync"

	"github.com/adarsh9780/inquira-ce/internal/apperror"
)

type Service struct {
	mu         sync.RWMutex
	repository Repository
	secrets    SecretStore
	provider   providerClient
}

func NewService(repository Repository, secrets SecretStore, httpClient HTTPDoer) *Service {
	return &Service{repository: repository, secrets: secrets, provider: providerClient{http: httpClient}}
}

func (s *Service) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.repository.Close()
}

func (s *Service) GetPreferences(ctx context.Context, providerHint string) (PreferencesResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_read_failed", "Could not load model settings.", err)
	}
	provider := preferences.LLMProvider
	if strings.TrimSpace(providerHint) != "" {
		provider = normalizeProvider(providerHint)
	}
	return s.response(preferences, provider)
}

func (s *Service) RuntimeConfiguration(ctx context.Context) (RuntimeConfiguration, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.runtimeConfiguration(ctx, RuntimeOverrides{}, false)
}

func (s *Service) SchemaRuntimeConfiguration(ctx context.Context) (RuntimeConfiguration, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.runtimeConfiguration(ctx, RuntimeOverrides{}, true)
}

func (s *Service) RuntimeConfigurationFor(ctx context.Context, overrides RuntimeOverrides, preferLite bool) (RuntimeConfiguration, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.runtimeConfiguration(ctx, overrides, preferLite)
}

func (s *Service) runtimeConfiguration(ctx context.Context, overrides RuntimeOverrides, preferLite bool) (RuntimeConfiguration, error) {
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return RuntimeConfiguration{}, apperror.Wrap("settings_read_failed", "Could not load model settings.", err)
	}
	defaultProvider := normalizeProvider(preferences.LLMProvider)
	provider := defaultProvider
	if overrides.Provider != nil && strings.TrimSpace(*overrides.Provider) != "" {
		provider = normalizeProvider(*overrides.Provider)
	}
	catalog := preferences.Catalogs[provider]
	mainModel := ""
	if provider == defaultProvider {
		mainModel = strings.TrimSpace(preferences.SelectedModel)
	}
	if mainModel == "" {
		mainModel = strings.TrimSpace(catalog.DefaultMainModel)
	}
	if overrides.MainModel != nil && strings.TrimSpace(*overrides.MainModel) != "" {
		mainModel = strings.TrimSpace(*overrides.MainModel)
	}
	liteModel := ""
	if provider == defaultProvider {
		liteModel = strings.TrimSpace(preferences.SelectedLiteModel)
		if liteModel == "" {
			liteModel = mainModel
		}
	} else {
		liteModel = strings.TrimSpace(catalog.DefaultLiteModel)
	}
	if liteModel == "" {
		liteModel = mainModel
	}
	if overrides.LiteModel != nil && strings.TrimSpace(*overrides.LiteModel) != "" {
		liteModel = strings.TrimSpace(*overrides.LiteModel)
	}
	codingModel := ""
	if provider == defaultProvider {
		codingModel = strings.TrimSpace(preferences.SelectedCodingModel)
		if codingModel == "" {
			codingModel = mainModel
		}
	} else {
		codingModel = mainModel
	}
	if overrides.CodingModel != nil && strings.TrimSpace(*overrides.CodingModel) != "" {
		codingModel = strings.TrimSpace(*overrides.CodingModel)
	}
	model := mainModel
	if preferLite {
		model = liteModel
	}
	if model == "" {
		model = catalog.DefaultMainModel
	}
	if model == "" {
		return RuntimeConfiguration{}, apperror.New("model_required", "Choose a model before starting an analysis.")
	}
	apiKey := ""
	if provider != "ollama" {
		apiKey, err = s.secrets.Get(provider)
		if err != nil {
			return RuntimeConfiguration{}, apperror.Wrap("keychain_read_failed", "Could not read the saved API key.", err)
		}
		if strings.TrimSpace(apiKey) == "" {
			return RuntimeConfiguration{}, apperror.New("missing_key", "Connect a model provider before starting an analysis.")
		}
	}
	baseURL := map[string]string{
		"openai":     "https://api.openai.com/v1",
		"openrouter": "https://openrouter.ai/api/v1",
		"ollama":     strings.TrimRight(strings.TrimSpace(preferences.OllamaBaseURL), "/"),
	}[provider]
	if baseURL == "" && provider == "ollama" {
		baseURL = "http://localhost:11434"
	}
	maxTokens := preferences.MaxTokens
	if overrides.MaxTokens != nil {
		maxTokens = *overrides.MaxTokens
	}
	if preferLite && maxTokens > 4096 {
		maxTokens = 4096
	}
	temperature := preferences.Temperature
	if overrides.Temperature != nil {
		temperature = *overrides.Temperature
	}
	topP := preferences.TopP
	if overrides.TopP != nil {
		topP = *overrides.TopP
	}
	allowDataSamples := preferences.AllowLLMDataSamples
	if overrides.AllowDataSamples != nil {
		allowDataSamples = *overrides.AllowDataSamples
	}
	return RuntimeConfiguration{
		Provider: provider, Model: model, LiteModel: liteModel, CodingModel: codingModel,
		APIKey: apiKey, BaseURL: baseURL,
		Temperature: temperature, MaxTokens: maxTokens, TopP: topP,
		TopK:             preferences.TopK,
		FrequencyPenalty: preferences.FrequencyPenalty, PresencePenalty: preferences.PresencePenalty,
		AllowDataSamples: allowDataSamples,
	}, nil
}

func (s *Service) GetOnboardingStatus(ctx context.Context) (OnboardingStatus, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return OnboardingStatus{}, apperror.Wrap("settings_read_failed", "Could not load onboarding status.", err)
	}
	ready, err := s.connectionReady(preferences)
	if err != nil {
		return OnboardingStatus{}, err
	}
	return OnboardingStatus{
		Completed: preferences.ModelOnboardingCompleted, ConnectionReady: ready,
		Provider: normalizeProvider(preferences.LLMProvider),
	}, nil
}

func (s *Service) CompleteOnboarding(ctx context.Context) (OnboardingStatus, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return OnboardingStatus{}, apperror.Wrap("settings_read_failed", "Could not load onboarding status.", err)
	}
	ready, err := s.connectionReady(preferences)
	if err != nil {
		return OnboardingStatus{}, err
	}
	if !ready {
		return OnboardingStatus{}, apperror.New("model_connection_required", "Connect and verify a model provider before continuing.")
	}
	preferences.ModelOnboardingCompleted = true
	if err := s.repository.Save(ctx, preferences); err != nil {
		return OnboardingStatus{}, apperror.Wrap("settings_write_failed", "Could not complete onboarding.", err)
	}
	return OnboardingStatus{Completed: true, ConnectionReady: true, Provider: normalizeProvider(preferences.LLMProvider)}, nil
}

func (s *Service) UpdatePreferences(ctx context.Context, request UpdateRequest) (PreferencesResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_read_failed", "Could not load model settings.", err)
	}
	if err := applyUpdate(&preferences, request); err != nil {
		return PreferencesResponse{}, err
	}
	normalizeSelections(&preferences, preferences.LLMProvider)
	if err := s.repository.Save(ctx, preferences); err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_write_failed", "Could not save model settings.", err)
	}
	return s.response(preferences, preferences.LLMProvider)
}

func (s *Service) VerifyKey(ctx context.Context, provider, key string) (VerifyResponse, error) {
	provider = normalizeProvider(provider)
	if provider != "ollama" && strings.TrimSpace(key) == "" {
		return VerifyResponse{}, apperror.New("missing_key", "API key cannot be empty.")
	}
	return s.provider.verify(ctx, provider, key), nil
}

func (s *Service) SaveConfiguration(ctx context.Context, request SaveRequest) (PreferencesResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_read_failed", "Could not load model settings.", err)
	}
	provider := normalizeProvider(request.Provider)
	key := strings.TrimSpace(valueOrEmpty(request.APIKey))
	if provider != "ollama" {
		if key == "" {
			key, err = s.secrets.Get(provider)
			if err != nil {
				return PreferencesResponse{}, apperror.Wrap("keychain_read_failed", "Could not read the saved API key.", err)
			}
		}
		if key == "" {
			return PreferencesResponse{}, apperror.New("missing_key", "An API key is required for this provider.")
		}
		if request.APIKey != nil {
			verification := s.provider.verify(ctx, provider, key)
			if !verification.Valid {
				return PreferencesResponse{}, apperror.New(verification.Error, verifyMessage(verification.Error))
			}
			if err := s.secrets.Set(provider, key); err != nil {
				return PreferencesResponse{}, apperror.Wrap("keychain_write_failed", "Could not save the API key in secure storage.", err)
			}
		}
	}

	preferences.LLMProvider = provider
	update := UpdateRequest{
		SelectedModel: request.SelectedModel, SelectedLiteModel: request.SelectedLiteModel,
		SelectedCodingModel: request.SelectedCodingModel, LLMTemperature: request.LLMTemperature,
		LLMMaxTokens: request.LLMMaxTokens, LLMTopP: request.LLMTopP, LLMTopK: request.LLMTopK,
		LLMFrequencyPenalty: request.LLMFrequencyPenalty, LLMPresencePenalty: request.LLMPresencePenalty,
		SlowRequestWarningSeconds: request.SlowRequestWarningSeconds,
		AllowLLMDataSamples:       request.AllowLLMDataSamples,
	}
	if err := applyUpdate(&preferences, update); err != nil {
		return PreferencesResponse{}, err
	}
	baseURL := preferences.OllamaBaseURL
	if request.BaseURL != nil {
		baseURL = strings.TrimRight(strings.TrimSpace(*request.BaseURL), "/")
		if !isValidBaseURL(baseURL) {
			return PreferencesResponse{}, apperror.New("invalid_base_url", "Enter a valid Ollama HTTP or HTTPS URL.")
		}
		preferences.OllamaBaseURL = baseURL
	}

	// Persist the credential and requested defaults even if a provider's model
	// catalog endpoint is temporarily unavailable.
	normalizeSelections(&preferences, provider)
	if err := s.repository.Save(ctx, preferences); err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_write_failed", "Could not save model settings.", err)
	}

	catalog, detail, _, refreshErr := s.provider.refresh(ctx, provider, key, baseURL)
	if refreshErr == nil {
		preferences.Catalogs[provider] = catalog
		normalizeSelections(&preferences, provider)
		if err := s.repository.Save(ctx, preferences); err != nil {
			return PreferencesResponse{}, apperror.Wrap("settings_write_failed", "Could not save the refreshed model list.", err)
		}
	}
	response, err := s.response(preferences, provider)
	if err != nil {
		return PreferencesResponse{}, err
	}
	response.Detail = detail
	if refreshErr != nil {
		response.Warning = "Configuration saved, but model refresh failed. Using the cached model list."
	}
	return response, nil
}

func (s *Service) RefreshModels(ctx context.Context, request RefreshRequest) (PreferencesResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_read_failed", "Could not load model settings.", err)
	}
	provider := normalizeProvider(request.Provider)
	key := strings.TrimSpace(valueOrEmpty(request.APIKey))
	if key == "" && provider != "ollama" {
		key, err = s.secrets.Get(provider)
		if err != nil {
			return PreferencesResponse{}, apperror.Wrap("keychain_read_failed", "Could not read the saved API key.", err)
		}
	}
	baseURL := preferences.OllamaBaseURL
	if request.BaseURL != nil && strings.TrimSpace(*request.BaseURL) != "" {
		baseURL = strings.TrimRight(strings.TrimSpace(*request.BaseURL), "/")
	}
	catalog, detail, errorCode, err := s.provider.refresh(ctx, provider, key, baseURL)
	if err != nil {
		message := "Could not refresh the provider model list. Check your network, proxy, and certificate settings."
		if errorCode == "ollama_unreachable" {
			message = "Could not reach Ollama at the configured base URL."
		}
		return PreferencesResponse{}, apperror.Wrap(errorCode, message, err)
	}
	preferences.Catalogs[provider] = catalog
	if provider == "ollama" {
		preferences.OllamaBaseURL = catalog.BaseURL
	}
	if preferences.LLMProvider == provider {
		normalizeSelections(&preferences, provider)
	}
	if err := s.repository.Save(ctx, preferences); err != nil {
		return PreferencesResponse{}, apperror.Wrap("settings_write_failed", "Could not save the refreshed model list.", err)
	}
	response, err := s.response(preferences, provider)
	response.Detail = detail
	return response, err
}

func (s *Service) SearchModels(ctx context.Context, provider, query string, limit int) (SearchResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	preferences, err := s.repository.Load(ctx)
	if err != nil {
		return SearchResponse{}, apperror.Wrap("settings_read_failed", "Could not load model settings.", err)
	}
	provider = normalizeProvider(provider)
	query = strings.ToLower(strings.TrimSpace(query))
	if len(query) < 2 {
		return SearchResponse{Provider: provider, Query: query, Models: []ModelEntry{}, Detail: "Found 0 models."}, nil
	}
	if limit < 1 {
		limit = 25
	}
	if limit > 50 {
		limit = 50
	}
	catalog := preferences.Catalogs[provider]
	results := make([]ModelEntry, 0, limit)
	for _, model := range catalog.Models {
		haystack := strings.ToLower(strings.Join([]string{model.ID, model.DisplayName, model.Provider, strings.Join(model.Tags, " "), strings.Join(model.RecommendedFor, " ")}, " "))
		if !strings.Contains(haystack, query) {
			continue
		}
		results = append(results, model)
		if len(results) == limit {
			break
		}
	}
	return SearchResponse{Provider: provider, Query: query, Models: results, Detail: fmt.Sprintf("Found %d models.", len(results))}, nil
}

func (s *Service) DeleteKey(ctx context.Context, provider string) (map[string]any, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	provider = normalizeProvider(provider)
	if provider == "ollama" {
		return nil, apperror.New("provider_has_no_key", "Ollama does not use a saved API key.")
	}
	if err := s.secrets.Delete(provider); err != nil {
		return nil, apperror.Wrap("keychain_delete_failed", "Could not remove the saved API key.", err)
	}
	return map[string]any{"message": "API key deleted.", "provider": provider}, nil
}

func (s *Service) response(preferences Preferences, provider string) (PreferencesResponse, error) {
	provider = normalizeProvider(provider)
	presence := make(map[string]bool, len(supportedProviders))
	for _, candidate := range supportedProviders {
		hasKey := false
		if candidate != "ollama" {
			var err error
			hasKey, err = s.secrets.Has(candidate)
			if err != nil {
				return PreferencesResponse{}, apperror.Wrap("keychain_read_failed", "Could not inspect secure API-key storage.", err)
			}
		}
		presence[candidate] = hasKey
	}
	catalog := preferences.Catalogs[provider]
	selectedMain := preferences.SelectedModel
	selectedLite := preferences.SelectedLiteModel
	selectedCoding := preferences.SelectedCodingModel
	if provider != preferences.LLMProvider {
		selectedMain = catalog.DefaultMainModel
		selectedLite = catalog.DefaultLiteModel
		selectedCoding = catalog.DefaultMainModel
	}
	mainModels := displayMainModels(provider, catalog, selectedMain)
	selectedPresent := presence[provider]
	return PreferencesResponse{
		LLMProvider: provider, AvailableProviders: append([]string{}, supportedProviders...),
		SelectedModel: selectedMain, SelectedLiteModel: selectedLite, SelectedCodingModel: selectedCoding,
		LLMTemperature: preferences.Temperature, LLMMaxTokens: preferences.MaxTokens,
		LLMTopP: preferences.TopP, LLMTopK: preferences.TopK,
		LLMFrequencyPenalty: preferences.FrequencyPenalty, LLMPresencePenalty: preferences.PresencePenalty,
		SlowRequestWarningSeconds: preferences.SlowRequestWarningSeconds,
		AllowLLMDataSamples:       preferences.AllowLLMDataSamples,
		EnabledModels:             mainModels, AvailableModels: mainModels,
		ProviderAvailableMainModels: mainModels, ProviderAvailableLiteModels: append([]string{}, catalog.LiteModels...),
		ProviderModelCatalogs: preferences.Catalogs, APIKeyPresentByProvider: presence,
		APIKeyPresent: selectedPresent, SelectedProviderRequiresAPIKey: provider != "ollama",
		SelectedProviderAPIKeyPresent: selectedPresent,
	}, nil
}

func applyUpdate(preferences *Preferences, request UpdateRequest) error {
	if request.LLMProvider != nil {
		preferences.LLMProvider = normalizeProvider(*request.LLMProvider)
	}
	if request.SelectedModel != nil {
		preferences.SelectedModel = strings.TrimSpace(*request.SelectedModel)
	}
	if request.SelectedLiteModel != nil {
		preferences.SelectedLiteModel = strings.TrimSpace(*request.SelectedLiteModel)
	}
	if request.SelectedCodingModel != nil {
		preferences.SelectedCodingModel = strings.TrimSpace(*request.SelectedCodingModel)
	}
	if request.LLMTemperature != nil {
		if *request.LLMTemperature < 0 || *request.LLMTemperature > 2 {
			return apperror.New("invalid_temperature", "Temperature must be between 0 and 2.")
		}
		preferences.Temperature = *request.LLMTemperature
	}
	if request.LLMMaxTokens != nil {
		if *request.LLMMaxTokens < 1 || *request.LLMMaxTokens > 131072 {
			return apperror.New("invalid_max_tokens", "Max tokens must be between 1 and 131072.")
		}
		preferences.MaxTokens = *request.LLMMaxTokens
	}
	if request.LLMTopP != nil {
		if *request.LLMTopP < 0 || *request.LLMTopP > 1 {
			return apperror.New("invalid_top_p", "Top P must be between 0 and 1.")
		}
		preferences.TopP = *request.LLMTopP
	}
	if request.LLMTopK != nil {
		if *request.LLMTopK < 0 || *request.LLMTopK > 500 {
			return apperror.New("invalid_top_k", "Top K must be between 0 and 500.")
		}
		preferences.TopK = *request.LLMTopK
	}
	if request.LLMFrequencyPenalty != nil {
		if *request.LLMFrequencyPenalty < -2 || *request.LLMFrequencyPenalty > 2 {
			return apperror.New("invalid_frequency_penalty", "Frequency penalty must be between -2 and 2.")
		}
		preferences.FrequencyPenalty = *request.LLMFrequencyPenalty
	}
	if request.LLMPresencePenalty != nil {
		if *request.LLMPresencePenalty < -2 || *request.LLMPresencePenalty > 2 {
			return apperror.New("invalid_presence_penalty", "Presence penalty must be between -2 and 2.")
		}
		preferences.PresencePenalty = *request.LLMPresencePenalty
	}
	if request.SlowRequestWarningSeconds != nil {
		if *request.SlowRequestWarningSeconds < 5 || *request.SlowRequestWarningSeconds > 600 {
			return apperror.New("invalid_slow_request_warning", "Slow-request warning must be between 5 and 600 seconds.")
		}
		preferences.SlowRequestWarningSeconds = *request.SlowRequestWarningSeconds
	}
	if request.AllowLLMDataSamples != nil {
		preferences.AllowLLMDataSamples = *request.AllowLLMDataSamples
	}
	return nil
}

func normalizeSelections(preferences *Preferences, provider string) {
	provider = normalizeProvider(provider)
	catalog := preferences.Catalogs[provider]
	if !contains(catalog.MainModels, preferences.SelectedModel) {
		preferences.SelectedModel = catalog.DefaultMainModel
	}
	if !contains(catalog.LiteModels, preferences.SelectedLiteModel) {
		preferences.SelectedLiteModel = catalog.DefaultLiteModel
	}
	if !contains(catalog.MainModels, preferences.SelectedCodingModel) {
		preferences.SelectedCodingModel = preferences.SelectedModel
	}
}

func valueOrEmpty(value *string) string {
	if value == nil {
		return ""
	}
	return *value
}

func verifyMessage(code string) string {
	switch code {
	case "quota_exceeded":
		return "The key is valid, but its provider quota is exhausted."
	case "network_error":
		return "Could not reach the provider. Check your network, proxy, and certificate settings."
	default:
		return "The provider rejected this API key."
	}
}

func (s *Service) connectionReady(preferences Preferences) (bool, error) {
	provider := normalizeProvider(preferences.LLMProvider)
	if provider == "ollama" {
		catalog := preferences.Catalogs[provider]
		return catalog.Source == "refreshed" && len(catalog.MainModels) > 0, nil
	}
	ready, err := s.secrets.Has(provider)
	if err != nil {
		return false, apperror.Wrap("keychain_read_failed", "Could not inspect secure API-key storage.", err)
	}
	return ready, nil
}
