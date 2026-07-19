package workspace

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"

	"inquira-go/internal/apperror"
	"inquira-go/internal/modelconfig"
)

type repository interface {
	List(context.Context) ([]Workspace, error)
	Get(context.Context, string) (Workspace, error)
	Create(context.Context, Workspace, string) (Workspace, error)
	Activate(context.Context, string) (Workspace, error)
	Update(context.Context, string, string, string, *string, time.Time) (Workspace, error)
	Delete(context.Context, string) error
	GetAIConfig(context.Context, string) (aiConfigRecord, error)
	SaveAIConfig(context.Context, aiConfigRecord, string) error
	ResetAIConfig(context.Context, string, string) error
	Close() error
}

type aiModelSource interface {
	GetPreferences(context.Context, string) (modelconfig.PreferencesResponse, error)
	RuntimeConfigurationFor(context.Context, modelconfig.RuntimeOverrides, bool) (modelconfig.RuntimeConfiguration, error)
}

type Service struct {
	repository repository
	models     aiModelSource
	now        func() time.Time
}

func NewService(repository repository) *Service {
	return &Service{repository: repository, now: time.Now}
}

func (s *Service) WithModelSource(models aiModelSource) *Service {
	s.models = models
	return s
}

func (s *Service) List(ctx context.Context) (ListResponse, error) {
	workspaces, err := s.repository.List(ctx)
	if err != nil {
		return ListResponse{}, apperror.Wrap("workspace_list_failed", "Could not load workspaces.", err)
	}
	return ListResponse{Workspaces: workspaces}, nil
}

func (s *Service) Create(ctx context.Context, request CreateRequest) (Workspace, error) {
	name, normalized, err := validateName(request.Name)
	if err != nil {
		return Workspace{}, err
	}
	now := s.now().UTC()
	created, err := s.repository.Create(ctx, Workspace{
		ID: uuid.NewString(), Name: name, SchemaContext: request.SchemaContext,
		CreatedAt: formatTime(now), UpdatedAt: formatTime(now),
	}, normalized)
	if err != nil {
		if isUniqueConstraint(err) {
			return Workspace{}, apperror.New("workspace_name_exists", "A workspace with this name already exists.")
		}
		return Workspace{}, apperror.Wrap("workspace_create_failed", "Could not create the workspace.", err)
	}
	return created, nil
}

func (s *Service) Activate(ctx context.Context, workspaceID string) (Workspace, error) {
	workspace, err := s.repository.Activate(ctx, strings.TrimSpace(workspaceID))
	if errors.Is(err, errNotFound) {
		return Workspace{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		return Workspace{}, apperror.Wrap("workspace_activate_failed", "Could not activate the workspace.", err)
	}
	return workspace, nil
}

func (s *Service) Update(ctx context.Context, request UpdateRequest) (Workspace, error) {
	name, normalized, err := validateName(request.Name)
	if err != nil {
		return Workspace{}, err
	}
	workspace, err := s.repository.Update(ctx, strings.TrimSpace(request.WorkspaceID), name, normalized,
		request.SchemaContext, s.now().UTC())
	if errors.Is(err, errNotFound) {
		return Workspace{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		if isUniqueConstraint(err) {
			return Workspace{}, apperror.New("workspace_name_exists", "A workspace with this name already exists.")
		}
		return Workspace{}, apperror.Wrap("workspace_update_failed", "Could not update the workspace.", err)
	}
	return workspace, nil
}

func (s *Service) Summary(ctx context.Context, workspaceID string) (Summary, error) {
	workspace, err := s.repository.Get(ctx, strings.TrimSpace(workspaceID))
	if errors.Is(err, errNotFound) {
		return Summary{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		return Summary{}, apperror.Wrap("workspace_summary_failed", "Could not load the workspace.", err)
	}
	return Summary{
		ID: workspace.ID, Name: workspace.Name, IsActive: workspace.IsActive,
		SchemaContext: workspace.SchemaContext, CreatedAt: workspace.CreatedAt,
		UpdatedAt: workspace.UpdatedAt, TableNames: []string{},
	}, nil
}

func (s *Service) Delete(ctx context.Context, workspaceID string) (DeletionResult, error) {
	id := strings.TrimSpace(workspaceID)
	if err := s.repository.Delete(ctx, id); errors.Is(err, errNotFound) {
		return DeletionResult{}, apperror.New("workspace_not_found", "Workspace not found.")
	} else if err != nil {
		return DeletionResult{}, apperror.Wrap("workspace_delete_failed", "Could not delete the workspace.", err)
	}
	now := s.now().UTC()
	return DeletionResult{
		JobID: uuid.NewString(), WorkspaceID: id, Status: "completed",
		CreatedAt: formatTime(now), UpdatedAt: formatTime(now),
	}, nil
}

func (s *Service) GetAIConfig(ctx context.Context, workspaceID string) (AIConfigResponse, error) {
	record, err := s.aiRecord(ctx, workspaceID)
	if err != nil {
		return AIConfigResponse{}, err
	}
	return s.resolveAIConfig(ctx, record)
}

func (s *Service) UpdateAIConfig(ctx context.Context, workspaceID string, request AIConfigUpdateRequest) (AIConfigResponse, error) {
	record, err := s.aiRecord(ctx, workspaceID)
	if err != nil {
		return AIConfigResponse{}, err
	}
	preferences, err := s.modelPreferences(ctx, "")
	if err != nil {
		return AIConfigResponse{}, err
	}
	provider, err := normalizeProviderOverride(request.LLMProviderOverride, preferences.AvailableProviders)
	if err != nil {
		return AIConfigResponse{}, err
	}
	mainModel, err := normalizeModelOverride(request.MainModelOverride)
	if err != nil {
		return AIConfigResponse{}, err
	}
	liteModel, err := normalizeModelOverride(request.LiteModelOverride)
	if err != nil {
		return AIConfigResponse{}, err
	}
	codingModel, err := normalizeModelOverride(request.CodingModelOverride)
	if err != nil {
		return AIConfigResponse{}, err
	}
	if request.LLMTemperatureOverride != nil && (*request.LLMTemperatureOverride < 0 || *request.LLMTemperatureOverride > 2) {
		return AIConfigResponse{}, apperror.New("workspace_ai_temperature_invalid", "Temperature must be between 0 and 2.")
	}
	if request.LLMMaxTokensOverride != nil && (*request.LLMMaxTokensOverride < 1 || *request.LLMMaxTokensOverride > 131072) {
		return AIConfigResponse{}, apperror.New("workspace_ai_max_tokens_invalid", "Max tokens must be between 1 and 131072.")
	}
	if request.LLMTopPOverride != nil && (*request.LLMTopPOverride < 0 || *request.LLMTopPOverride > 1) {
		return AIConfigResponse{}, apperror.New("workspace_ai_top_p_invalid", "Top P must be between 0 and 1.")
	}
	record.Provider = provider
	record.MainModel = mainModel
	record.LiteModel = liteModel
	record.CodingModel = codingModel
	record.Temperature = request.LLMTemperatureOverride
	record.MaxTokens = request.LLMMaxTokensOverride
	record.TopP = request.LLMTopPOverride
	record.AllowDataSamples = request.AllowLLMDataSamples
	record.ConfigurationReviewed = true
	if err := s.repository.SaveAIConfig(ctx, record, formatTime(s.now().UTC())); err != nil {
		return AIConfigResponse{}, apperror.Wrap("workspace_ai_update_failed", "Could not save workspace AI settings.", err)
	}
	return s.resolveAIConfig(ctx, record)
}

func (s *Service) ResetAIConfig(ctx context.Context, workspaceID string) (AIConfigResponse, error) {
	record, err := s.aiRecord(ctx, workspaceID)
	if err != nil {
		return AIConfigResponse{}, err
	}
	if err := s.repository.ResetAIConfig(ctx, record.WorkspaceID, formatTime(s.now().UTC())); err != nil {
		return AIConfigResponse{}, apperror.Wrap("workspace_ai_reset_failed", "Could not reset workspace AI settings.", err)
	}
	record, err = s.aiRecord(ctx, record.WorkspaceID)
	if err != nil {
		return AIConfigResponse{}, err
	}
	return s.resolveAIConfig(ctx, record)
}

func (s *Service) RuntimeConfiguration(ctx context.Context, workspaceID string) (modelconfig.RuntimeConfiguration, error) {
	return s.runtimeConfiguration(ctx, workspaceID, false)
}

func (s *Service) SchemaRuntimeConfiguration(ctx context.Context, workspaceID string) (modelconfig.RuntimeConfiguration, error) {
	return s.runtimeConfiguration(ctx, workspaceID, true)
}

func (s *Service) runtimeConfiguration(ctx context.Context, workspaceID string, preferLite bool) (modelconfig.RuntimeConfiguration, error) {
	record, err := s.aiRecord(ctx, workspaceID)
	if err != nil {
		return modelconfig.RuntimeConfiguration{}, err
	}
	if s.models == nil {
		return modelconfig.RuntimeConfiguration{}, apperror.New("model_configuration_unavailable", "Model configuration is unavailable.")
	}
	allowSamples := record.AllowDataSamples
	return s.models.RuntimeConfigurationFor(ctx, modelconfig.RuntimeOverrides{
		Provider: record.Provider, MainModel: record.MainModel, LiteModel: record.LiteModel,
		CodingModel: record.CodingModel, Temperature: record.Temperature,
		MaxTokens: record.MaxTokens, TopP: record.TopP, AllowDataSamples: &allowSamples,
	}, preferLite)
}

func (s *Service) aiRecord(ctx context.Context, workspaceID string) (aiConfigRecord, error) {
	id := strings.TrimSpace(workspaceID)
	if id == "" {
		return aiConfigRecord{}, apperror.New("workspace_required", "Workspace identity is required.")
	}
	record, err := s.repository.GetAIConfig(ctx, id)
	if errors.Is(err, errNotFound) {
		return aiConfigRecord{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		return aiConfigRecord{}, apperror.Wrap("workspace_ai_read_failed", "Could not load workspace AI settings.", err)
	}
	return record, nil
}

func (s *Service) modelPreferences(ctx context.Context, provider string) (modelconfig.PreferencesResponse, error) {
	if s.models == nil {
		return modelconfig.PreferencesResponse{}, apperror.New("model_configuration_unavailable", "Model configuration is unavailable.")
	}
	preferences, err := s.models.GetPreferences(ctx, provider)
	if err != nil {
		return modelconfig.PreferencesResponse{}, err
	}
	return preferences, nil
}

func (s *Service) resolveAIConfig(ctx context.Context, record aiConfigRecord) (AIConfigResponse, error) {
	defaultsPreferences, err := s.modelPreferences(ctx, "")
	if err != nil {
		return AIConfigResponse{}, err
	}
	defaultCoding := strings.TrimSpace(defaultsPreferences.SelectedCodingModel)
	if defaultCoding == "" {
		defaultCoding = strings.TrimSpace(defaultsPreferences.SelectedModel)
	}
	defaults := AIConfigDefaults{
		Provider: defaultsPreferences.LLMProvider, MainModel: defaultsPreferences.SelectedModel,
		LiteModel: defaultsPreferences.SelectedLiteModel, CodingModel: defaultCoding,
		Temperature: defaultsPreferences.LLMTemperature, MaxTokens: defaultsPreferences.LLMMaxTokens,
		TopP: defaultsPreferences.LLMTopP,
	}
	effectiveProvider := defaults.Provider
	if record.Provider != nil {
		effectiveProvider = *record.Provider
	}
	effectivePreferences := defaultsPreferences
	if effectiveProvider != defaults.Provider {
		effectivePreferences, err = s.modelPreferences(ctx, effectiveProvider)
		if err != nil {
			return AIConfigResponse{}, err
		}
	}
	baseMain := strings.TrimSpace(effectivePreferences.SelectedModel)
	baseLite := strings.TrimSpace(effectivePreferences.SelectedLiteModel)
	baseCoding := strings.TrimSpace(effectivePreferences.SelectedCodingModel)
	if baseLite == "" {
		baseLite = baseMain
	}
	if baseCoding == "" {
		baseCoding = baseMain
	}
	effective := AIConfigEffective{
		Provider: effectiveProvider, MainModel: valueOr(record.MainModel, baseMain),
		LiteModel: valueOr(record.LiteModel, baseLite), CodingModel: valueOr(record.CodingModel, baseCoding),
		Temperature: floatOr(record.Temperature, defaults.Temperature),
		MaxTokens:   intOr(record.MaxTokens, defaults.MaxTokens), TopP: floatOr(record.TopP, defaults.TopP),
		AllowLLMDataSamples: record.AllowDataSamples,
		Sources: map[string]string{
			"provider": sourceOf(record.Provider), "main_model": sourceOf(record.MainModel),
			"lite_model": sourceOf(record.LiteModel), "coding_model": sourceOf(record.CodingModel),
			"temperature": sourceOf(record.Temperature), "max_tokens": sourceOf(record.MaxTokens),
			"top_p": sourceOf(record.TopP), "allow_llm_data_samples": "workspace",
		},
	}
	requiresKey := effective.Provider != "ollama"
	credentialReady := !requiresKey || defaultsPreferences.APIKeyPresentByProvider[effective.Provider]
	modelReady := effective.MainModel != "" && effective.LiteModel != "" && effective.CodingModel != ""
	return AIConfigResponse{
		WorkspaceID: record.WorkspaceID, Defaults: defaults,
		Overrides: AIConfigOverrides{
			Provider: record.Provider, MainModel: record.MainModel, LiteModel: record.LiteModel,
			CodingModel: record.CodingModel, Temperature: record.Temperature,
			MaxTokens: record.MaxTokens, TopP: record.TopP, AllowLLMDataSamples: record.AllowDataSamples,
		},
		Effective: effective,
		Readiness: AIConfigReadiness{
			CredentialReady: credentialReady, ModelReady: modelReady,
			ConfigurationReviewed: record.ConfigurationReviewed,
			Ready:                 credentialReady && modelReady && record.ConfigurationReviewed,
			CredentialSource:      "application", RequiresAPIKey: requiresKey,
		},
	}, nil
}

func (s *Service) Close() error { return s.repository.Close() }

func validateName(value string) (string, string, error) {
	name := strings.TrimSpace(value)
	if name == "" {
		return "", "", apperror.New("workspace_name_required", "Workspace name cannot be empty.")
	}
	if len([]rune(name)) > maxNameLength {
		return "", "", apperror.New("workspace_name_too_long", fmt.Sprintf("Workspace name must be %d characters or fewer.", maxNameLength))
	}
	normalized := strings.ToLower(strings.Join(strings.Fields(name), " "))
	return name, normalized, nil
}

func isUniqueConstraint(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "unique constraint") || strings.Contains(message, "constraint failed")
}

func normalizeProviderOverride(value *string, available []string) (*string, error) {
	if value == nil || strings.TrimSpace(*value) == "" {
		return nil, nil
	}
	provider := strings.ToLower(strings.TrimSpace(*value))
	for _, candidate := range available {
		if provider == strings.ToLower(strings.TrimSpace(candidate)) {
			return &provider, nil
		}
	}
	return nil, apperror.New("workspace_ai_provider_invalid", "Choose a supported model provider.")
}

func normalizeModelOverride(value *string) (*string, error) {
	if value == nil || strings.TrimSpace(*value) == "" {
		return nil, nil
	}
	model := strings.TrimSpace(*value)
	if len([]rune(model)) > 255 {
		return nil, apperror.New("workspace_ai_model_invalid", "Workspace model names must be 255 characters or fewer.")
	}
	return &model, nil
}

func valueOr(value *string, fallback string) string {
	if value != nil {
		return *value
	}
	return fallback
}

func floatOr(value *float64, fallback float64) float64 {
	if value != nil {
		return *value
	}
	return fallback
}

func intOr(value *int, fallback int) int {
	if value != nil {
		return *value
	}
	return fallback
}

func sourceOf[T any](value *T) string {
	if value != nil {
		return "workspace"
	}
	return "application"
}
