package workspace

import (
	"context"
	"errors"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"inquira-go/internal/apperror"
	"inquira-go/internal/modelconfig"
)

type fakeWorkspaceModels struct {
	preferences modelconfig.PreferencesResponse
	requests    []modelconfig.RuntimeOverrides
	preferLite  []bool
}

func (f *fakeWorkspaceModels) GetPreferences(context.Context, string) (modelconfig.PreferencesResponse, error) {
	return f.preferences, nil
}

func (f *fakeWorkspaceModels) RuntimeConfigurationFor(_ context.Context, overrides modelconfig.RuntimeOverrides, preferLite bool) (modelconfig.RuntimeConfiguration, error) {
	f.requests = append(f.requests, overrides)
	f.preferLite = append(f.preferLite, preferLite)
	model := "workspace-main"
	if preferLite {
		model = "workspace-lite"
	}
	return modelconfig.RuntimeConfiguration{Provider: "anthropic", Model: model, AllowDataSamples: overrides.AllowDataSamples != nil && *overrides.AllowDataSamples}, nil
}

func TestWorkspaceLifecyclePersistsAndMaintainsOneActiveWorkspace(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "inquira.db")
	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatalf("OpenSQLite() error = %v", err)
	}
	service := NewService(repository)
	clock := time.Date(2026, 7, 17, 8, 0, 0, 0, time.UTC)
	service.now = func() time.Time {
		clock = clock.Add(time.Second)
		return clock
	}
	ctx := context.Background()

	first, err := service.Create(ctx, CreateRequest{Name: "  Sales  ", SchemaContext: "Revenue definitions"})
	if err != nil {
		t.Fatalf("Create(first) error = %v", err)
	}
	if first.Name != "Sales" || !first.IsActive || first.SchemaContext != "Revenue definitions" {
		t.Fatalf("first workspace = %#v", first)
	}
	second, err := service.Create(ctx, CreateRequest{Name: "Operations"})
	if err != nil {
		t.Fatalf("Create(second) error = %v", err)
	}
	if second.IsActive {
		t.Fatal("second workspace should not replace the active workspace")
	}
	activated, err := service.Activate(ctx, second.ID)
	if err != nil || !activated.IsActive {
		t.Fatalf("Activate() = %#v, %v", activated, err)
	}
	contextUpdate := "Updated operational context"
	updated, err := service.Update(ctx, UpdateRequest{
		WorkspaceID: second.ID, Name: "Operations 2026", SchemaContext: &contextUpdate,
	})
	if err != nil {
		t.Fatalf("Update() error = %v", err)
	}
	if updated.Name != "Operations 2026" || updated.SchemaContext != contextUpdate {
		t.Fatalf("updated workspace = %#v", updated)
	}

	if err := service.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := OpenSQLite(path)
	if err != nil {
		t.Fatalf("reopen error = %v", err)
	}
	service = NewService(reopened)
	defer service.Close()
	listed, err := service.List(ctx)
	if err != nil {
		t.Fatalf("List() error = %v", err)
	}
	if len(listed.Workspaces) != 2 || listed.Workspaces[0].ID != second.ID || !listed.Workspaces[0].IsActive {
		t.Fatalf("persisted workspaces = %#v", listed.Workspaces)
	}

	if _, err := service.Delete(ctx, second.ID); err != nil {
		t.Fatalf("Delete(active) error = %v", err)
	}
	listed, err = service.List(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(listed.Workspaces) != 1 || listed.Workspaces[0].ID != first.ID || !listed.Workspaces[0].IsActive {
		t.Fatalf("fallback workspace = %#v", listed.Workspaces)
	}
}

func TestWorkspaceNamesAreValidatedAndCaseInsensitiveUnique(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository)
	defer service.Close()
	ctx := context.Background()

	if _, err := service.Create(ctx, CreateRequest{Name: "   "}); errorCode(err) != "workspace_name_required" {
		t.Fatalf("blank name error = %v", err)
	}
	if _, err := service.Create(ctx, CreateRequest{Name: "Quarterly   Results"}); err != nil {
		t.Fatal(err)
	}
	if _, err := service.Create(ctx, CreateRequest{Name: " quarterly results "}); errorCode(err) != "workspace_name_exists" {
		t.Fatalf("duplicate name error = %v", err)
	}
}

func TestWorkspaceSummaryDefersDataCounts(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository)
	defer service.Close()
	created, err := service.Create(context.Background(), CreateRequest{Name: "Research"})
	if err != nil {
		t.Fatal(err)
	}
	summary, err := service.Summary(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if summary.TableCount != 0 || summary.ConversationCount != 0 || summary.TableNames == nil {
		t.Fatalf("summary = %#v", summary)
	}
}

func TestDeletingLastWorkspaceLetsNextWorkspaceBecomeActive(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	service := NewService(repository)
	defer service.Close()
	ctx := context.Background()
	first, err := service.Create(ctx, CreateRequest{Name: "First"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := service.Delete(ctx, first.ID); err != nil {
		t.Fatal(err)
	}
	second, err := service.Create(ctx, CreateRequest{Name: "Second"})
	if err != nil {
		t.Fatal(err)
	}
	if !second.IsActive {
		t.Fatal("workspace created after deleting the last workspace should be active")
	}
}

func TestWorkspaceAIConfigurationPersistsAndResolvesOverrides(t *testing.T) {
	path := filepath.Join(t.TempDir(), "inquira.db")
	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatal(err)
	}
	models := &fakeWorkspaceModels{preferences: modelconfig.PreferencesResponse{
		LLMProvider: "openai", SelectedModel: "gpt-main", SelectedLiteModel: "gpt-lite", SelectedCodingModel: "gpt-code",
		LLMTemperature: 0.7, LLMMaxTokens: 8000, LLMTopP: 1,
		AvailableProviders:      []string{"openai", "anthropic", "ollama"},
		APIKeyPresentByProvider: map[string]bool{"openai": true, "anthropic": true},
	}}
	service := NewService(repository).WithModelSource(models)
	created, err := service.Create(context.Background(), CreateRequest{Name: "Analysis"})
	if err != nil {
		t.Fatal(err)
	}
	initial, err := service.GetAIConfig(context.Background(), created.ID)
	if err != nil {
		t.Fatal(err)
	}
	if initial.Defaults.MainModel != "gpt-main" || initial.Effective.CodingModel != "gpt-code" ||
		initial.Effective.Sources["main_model"] != "application" || initial.Effective.Sources["temperature"] != "application" ||
		initial.Readiness.ConfigurationReviewed || initial.Readiness.Ready {
		t.Fatalf("initial AI config = %#v", initial)
	}

	provider, mainModel, liteModel, codingModel := "anthropic", "claude-main", "claude-lite", "claude-code"
	temperature, maxTokens, topP := 0.2, 12000, 0.85
	updated, err := service.UpdateAIConfig(context.Background(), created.ID, AIConfigUpdateRequest{
		LLMProviderOverride: &provider, MainModelOverride: &mainModel, LiteModelOverride: &liteModel,
		CodingModelOverride: &codingModel, LLMTemperatureOverride: &temperature,
		LLMMaxTokensOverride: &maxTokens, LLMTopPOverride: &topP, AllowLLMDataSamples: true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if updated.Effective.Provider != provider || updated.Effective.MainModel != mainModel || updated.Effective.LiteModel != liteModel ||
		updated.Effective.CodingModel != codingModel || !updated.Effective.AllowLLMDataSamples ||
		updated.Effective.Sources["main_model"] != "workspace" || !updated.Readiness.Ready {
		t.Fatalf("updated AI config = %#v", updated)
	}
	runtimeConfig, err := service.RuntimeConfiguration(context.Background(), created.ID)
	if err != nil || runtimeConfig.Model != "workspace-main" || len(models.requests) != 1 || models.requests[0].CodingModel == nil || *models.requests[0].CodingModel != codingModel {
		t.Fatalf("runtime config=%#v requests=%#v error=%v", runtimeConfig, models.requests, err)
	}
	schemaConfig, err := service.SchemaRuntimeConfiguration(context.Background(), created.ID)
	if err != nil || schemaConfig.Model != "workspace-lite" || len(models.preferLite) != 2 || !models.preferLite[1] {
		t.Fatalf("schema config=%#v preferLite=%#v error=%v", schemaConfig, models.preferLite, err)
	}

	if err := service.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := OpenSQLite(path)
	if err != nil {
		t.Fatal(err)
	}
	service = NewService(reopened).WithModelSource(models)
	defer service.Close()
	persisted, err := service.GetAIConfig(context.Background(), created.ID)
	if err != nil || persisted.Overrides.MainModel == nil || *persisted.Overrides.MainModel != mainModel || !persisted.Readiness.ConfigurationReviewed {
		t.Fatalf("persisted AI config = %#v, %v", persisted, err)
	}
}

func TestWorkspaceAIConfigurationValidatesInputAndOwnership(t *testing.T) {
	repository, err := OpenSQLite(filepath.Join(t.TempDir(), "inquira.db"))
	if err != nil {
		t.Fatal(err)
	}
	models := &fakeWorkspaceModels{preferences: modelconfig.PreferencesResponse{AvailableProviders: []string{"openai"}}}
	service := NewService(repository).WithModelSource(models)
	defer service.Close()
	created, err := service.Create(context.Background(), CreateRequest{Name: "Analysis"})
	if err != nil {
		t.Fatal(err)
	}
	unsupported := "unknown"
	temperature := 3.0
	negativeTemperature := -0.1
	maxTokensTooLow, maxTokensTooHigh := 0, 131073
	topPTooLow, topPTooHigh := -0.1, 1.1
	longModel := strings.Repeat("m", 256)
	for _, test := range []struct {
		request AIConfigUpdateRequest
		code    string
	}{
		{AIConfigUpdateRequest{LLMProviderOverride: &unsupported}, "workspace_ai_provider_invalid"},
		{AIConfigUpdateRequest{LLMTemperatureOverride: &temperature}, "workspace_ai_temperature_invalid"},
		{AIConfigUpdateRequest{LLMTemperatureOverride: &negativeTemperature}, "workspace_ai_temperature_invalid"},
		{AIConfigUpdateRequest{LLMMaxTokensOverride: &maxTokensTooLow}, "workspace_ai_max_tokens_invalid"},
		{AIConfigUpdateRequest{LLMMaxTokensOverride: &maxTokensTooHigh}, "workspace_ai_max_tokens_invalid"},
		{AIConfigUpdateRequest{LLMTopPOverride: &topPTooLow}, "workspace_ai_top_p_invalid"},
		{AIConfigUpdateRequest{LLMTopPOverride: &topPTooHigh}, "workspace_ai_top_p_invalid"},
		{AIConfigUpdateRequest{MainModelOverride: &longModel}, "workspace_ai_model_invalid"},
	} {
		if _, err := service.UpdateAIConfig(context.Background(), created.ID, test.request); errorCode(err) != test.code {
			t.Fatalf("request=%#v error=%v", test.request, err)
		}
	}
	if _, err := service.GetAIConfig(context.Background(), "missing"); errorCode(err) != "workspace_not_found" {
		t.Fatalf("missing workspace error = %v", err)
	}
}

func errorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
