package modelconfig

type ModelEntry struct {
	ID             string   `json:"id"`
	DisplayName    string   `json:"display_name"`
	Provider       string   `json:"provider"`
	ContextWindow  int      `json:"context_window"`
	RecommendedFor []string `json:"recommended_for"`
	Tags           []string `json:"tags"`
}

type Catalog struct {
	MainModels              []string     `json:"main_models"`
	LiteModels              []string     `json:"lite_models"`
	DefaultMainModel        string       `json:"default_main_model"`
	DefaultLiteModel        string       `json:"default_lite_model"`
	BaseURL                 string       `json:"base_url"`
	Source                  string       `json:"source"`
	AccountModelsConfigured *bool        `json:"account_models_configured"`
	AccountModelsURL        string       `json:"account_models_url"`
	Models                  []ModelEntry `json:"models"`
}

type Preferences struct {
	LLMProvider               string
	SelectedModel             string
	SelectedLiteModel         string
	SelectedCodingModel       string
	Temperature               float64
	MaxTokens                 int
	TopP                      float64
	TopK                      int
	FrequencyPenalty          float64
	PresencePenalty           float64
	SlowRequestWarningSeconds int
	AllowLLMDataSamples       bool
	OllamaBaseURL             string
	Catalogs                  map[string]Catalog
}

type PreferencesResponse struct {
	LLMProvider                    string             `json:"llm_provider"`
	AvailableProviders             []string           `json:"available_providers"`
	SelectedModel                  string             `json:"selected_model"`
	SelectedLiteModel              string             `json:"selected_lite_model"`
	SelectedCodingModel            string             `json:"selected_coding_model"`
	LLMTemperature                 float64            `json:"llm_temperature"`
	LLMMaxTokens                   int                `json:"llm_max_tokens"`
	LLMTopP                        float64            `json:"llm_top_p"`
	LLMTopK                        int                `json:"llm_top_k"`
	LLMFrequencyPenalty            float64            `json:"llm_frequency_penalty"`
	LLMPresencePenalty             float64            `json:"llm_presence_penalty"`
	SlowRequestWarningSeconds      int                `json:"slow_request_warning_seconds"`
	AllowLLMDataSamples            bool               `json:"allow_llm_data_samples"`
	EnabledModels                  []string           `json:"enabled_models"`
	APIKeyPresent                  bool               `json:"api_key_present"`
	AvailableModels                []string           `json:"available_models"`
	ProviderAvailableMainModels    []string           `json:"provider_available_main_models"`
	ProviderAvailableLiteModels    []string           `json:"provider_available_lite_models"`
	ProviderModelCatalogs          map[string]Catalog `json:"provider_model_catalogs"`
	APIKeyPresentByProvider        map[string]bool    `json:"api_key_present_by_provider"`
	SelectedProviderRequiresAPIKey bool               `json:"selected_provider_requires_api_key"`
	SelectedProviderAPIKeyPresent  bool               `json:"selected_provider_api_key_present"`
	Detail                         string             `json:"detail,omitempty"`
	Warning                        string             `json:"warning,omitempty"`
	Error                          string             `json:"error,omitempty"`
}

type UpdateRequest struct {
	LLMProvider               *string  `json:"llm_provider"`
	SelectedModel             *string  `json:"selected_model"`
	SelectedLiteModel         *string  `json:"selected_lite_model"`
	SelectedCodingModel       *string  `json:"selected_coding_model"`
	LLMTemperature            *float64 `json:"llm_temperature"`
	LLMMaxTokens              *int     `json:"llm_max_tokens"`
	LLMTopP                   *float64 `json:"llm_top_p"`
	LLMTopK                   *int     `json:"llm_top_k"`
	LLMFrequencyPenalty       *float64 `json:"llm_frequency_penalty"`
	LLMPresencePenalty        *float64 `json:"llm_presence_penalty"`
	SlowRequestWarningSeconds *int     `json:"slow_request_warning_seconds"`
	AllowLLMDataSamples       *bool    `json:"allow_llm_data_samples"`
}

type SaveRequest struct {
	Provider                  string   `json:"provider"`
	APIKey                    *string  `json:"api_key"`
	BaseURL                   *string  `json:"base_url"`
	SelectedModel             *string  `json:"selected_model"`
	SelectedLiteModel         *string  `json:"selected_lite_model"`
	SelectedCodingModel       *string  `json:"selected_coding_model"`
	LLMTemperature            *float64 `json:"llm_temperature"`
	LLMMaxTokens              *int     `json:"llm_max_tokens"`
	LLMTopP                   *float64 `json:"llm_top_p"`
	LLMTopK                   *int     `json:"llm_top_k"`
	LLMFrequencyPenalty       *float64 `json:"llm_frequency_penalty"`
	LLMPresencePenalty        *float64 `json:"llm_presence_penalty"`
	SlowRequestWarningSeconds *int     `json:"slow_request_warning_seconds"`
	AllowLLMDataSamples       *bool    `json:"allow_llm_data_samples"`
}

type RefreshRequest struct {
	Provider string  `json:"provider"`
	APIKey   *string `json:"api_key"`
	BaseURL  *string `json:"base_url"`
}

type VerifyResponse struct {
	Valid bool   `json:"valid"`
	Error string `json:"error"`
}

type SearchResponse struct {
	Provider string       `json:"provider"`
	Query    string       `json:"query"`
	Models   []ModelEntry `json:"models"`
	Detail   string       `json:"detail"`
	Error    string       `json:"error"`
}
