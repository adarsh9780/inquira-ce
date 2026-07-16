package modelconfig

import (
	"context"
	"path/filepath"
	"testing"
)

func TestSQLiteRepositoryMigratesAndPersistsModelPreferences(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "inquira.db")
	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatalf("OpenSQLite() error = %v", err)
	}
	defer repository.Close()

	preferences, err := repository.Load(context.Background())
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if preferences.LLMProvider != "openrouter" {
		t.Fatalf("default provider = %q", preferences.LLMProvider)
	}

	preferences.LLMProvider = "openai"
	preferences.SelectedModel = "gpt-4.1"
	preferences.AllowLLMDataSamples = true
	if err := repository.Save(context.Background(), preferences); err != nil {
		t.Fatalf("Save() error = %v", err)
	}

	reloaded, err := repository.Load(context.Background())
	if err != nil {
		t.Fatalf("second Load() error = %v", err)
	}
	if reloaded.LLMProvider != "openai" || reloaded.SelectedModel != "gpt-4.1" || !reloaded.AllowLLMDataSamples {
		t.Fatalf("persisted preferences = %#v", reloaded)
	}
}
