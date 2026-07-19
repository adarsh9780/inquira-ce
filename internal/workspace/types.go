package workspace

const maxNameLength = 120

type Workspace struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	IsActive      bool   `json:"is_active"`
	DuckDBPath    string `json:"duckdb_path"`
	SchemaContext string `json:"schema_context"`
	CreatedAt     string `json:"created_at"`
	UpdatedAt     string `json:"updated_at"`
}

type ListResponse struct {
	Workspaces []Workspace `json:"workspaces"`
}

type CreateRequest struct {
	Name          string `json:"name"`
	SchemaContext string `json:"schema_context"`
}

type UpdateRequest struct {
	WorkspaceID   string  `json:"workspace_id"`
	Name          string  `json:"name"`
	SchemaContext *string `json:"schema_context"`
}

type Summary struct {
	ID                string   `json:"id"`
	Name              string   `json:"name"`
	IsActive          bool     `json:"is_active"`
	SchemaContext     string   `json:"schema_context"`
	CreatedAt         string   `json:"created_at"`
	UpdatedAt         string   `json:"updated_at"`
	TableCount        int      `json:"table_count"`
	TableNames        []string `json:"table_names"`
	ConversationCount int      `json:"conversation_count"`
}

type DeletionResult struct {
	JobID        string  `json:"job_id"`
	WorkspaceID  string  `json:"workspace_id"`
	Status       string  `json:"status"`
	ErrorMessage *string `json:"error_message"`
	CreatedAt    string  `json:"created_at"`
	UpdatedAt    string  `json:"updated_at"`
}

type AIConfigUpdateRequest struct {
	LLMProviderOverride    *string  `json:"llm_provider_override"`
	MainModelOverride      *string  `json:"main_model_override"`
	LiteModelOverride      *string  `json:"lite_model_override"`
	CodingModelOverride    *string  `json:"coding_model_override"`
	LLMTemperatureOverride *float64 `json:"llm_temperature_override"`
	LLMMaxTokensOverride   *int     `json:"llm_max_tokens_override"`
	LLMTopPOverride        *float64 `json:"llm_top_p_override"`
	AllowLLMDataSamples    bool     `json:"allow_llm_data_samples"`
}

type AIConfigDefaults struct {
	Provider    string  `json:"provider"`
	MainModel   string  `json:"main_model"`
	LiteModel   string  `json:"lite_model"`
	CodingModel string  `json:"coding_model"`
	Temperature float64 `json:"temperature"`
	MaxTokens   int     `json:"max_tokens"`
	TopP        float64 `json:"top_p"`
}

type AIConfigOverrides struct {
	Provider            *string  `json:"provider"`
	MainModel           *string  `json:"main_model"`
	LiteModel           *string  `json:"lite_model"`
	CodingModel         *string  `json:"coding_model"`
	Temperature         *float64 `json:"temperature"`
	MaxTokens           *int     `json:"max_tokens"`
	TopP                *float64 `json:"top_p"`
	AllowLLMDataSamples bool     `json:"allow_llm_data_samples"`
}

type AIConfigEffective struct {
	Provider            string            `json:"provider"`
	MainModel           string            `json:"main_model"`
	LiteModel           string            `json:"lite_model"`
	CodingModel         string            `json:"coding_model"`
	Temperature         float64           `json:"temperature"`
	MaxTokens           int               `json:"max_tokens"`
	TopP                float64           `json:"top_p"`
	AllowLLMDataSamples bool              `json:"allow_llm_data_samples"`
	Sources             map[string]string `json:"sources"`
}

type AIConfigReadiness struct {
	CredentialReady       bool   `json:"credential_ready"`
	ModelReady            bool   `json:"model_ready"`
	ConfigurationReviewed bool   `json:"configuration_reviewed"`
	Ready                 bool   `json:"ready"`
	CredentialSource      string `json:"credential_source"`
	RequiresAPIKey        bool   `json:"requires_api_key"`
}

type AIConfigResponse struct {
	WorkspaceID string            `json:"workspace_id"`
	Defaults    AIConfigDefaults  `json:"defaults"`
	Overrides   AIConfigOverrides `json:"overrides"`
	Effective   AIConfigEffective `json:"effective"`
	Readiness   AIConfigReadiness `json:"readiness"`
}

type aiConfigRecord struct {
	WorkspaceID           string
	Provider              *string
	MainModel             *string
	LiteModel             *string
	CodingModel           *string
	Temperature           *float64
	MaxTokens             *int
	TopP                  *float64
	AllowDataSamples      bool
	ConfigurationReviewed bool
}
