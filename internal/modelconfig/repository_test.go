package modelconfig

import (
	"context"
	"database/sql"
	"encoding/json"
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
	if preferences.ModelOnboardingCompleted {
		t.Fatal("fresh repository should require onboarding")
	}
	var migrationCount int
	if err := repository.db.QueryRow(`SELECT COUNT(*) FROM schema_migrations`).Scan(&migrationCount); err != nil {
		t.Fatal(err)
	}
	if migrationCount != 2 {
		t.Fatalf("migration count = %d", migrationCount)
	}

	preferences.LLMProvider = "openai"
	preferences.SelectedModel = "gpt-4.1"
	preferences.AllowLLMDataSamples = true
	preferences.ModelOnboardingCompleted = true
	if err := repository.Save(context.Background(), preferences); err != nil {
		t.Fatalf("Save() error = %v", err)
	}

	reloaded, err := repository.Load(context.Background())
	if err != nil {
		t.Fatalf("second Load() error = %v", err)
	}
	if reloaded.LLMProvider != "openai" || reloaded.SelectedModel != "gpt-4.1" || !reloaded.AllowLLMDataSamples || !reloaded.ModelOnboardingCompleted {
		t.Fatalf("persisted preferences = %#v", reloaded)
	}
}

func TestSQLiteRepositoryMigratesExistingFoundationDatabase(t *testing.T) {
	path := filepath.Join(t.TempDir(), "inquira.db")
	db, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	statements := []string{
		`CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)`,
		`INSERT INTO schema_migrations(version) VALUES (1)`,
		`CREATE TABLE model_preferences (
			id INTEGER PRIMARY KEY CHECK (id = 1), llm_provider TEXT NOT NULL,
			selected_model TEXT NOT NULL, selected_lite_model TEXT NOT NULL,
			selected_coding_model TEXT NOT NULL, llm_temperature REAL NOT NULL,
			llm_max_tokens INTEGER NOT NULL, llm_top_p REAL NOT NULL,
			llm_top_k INTEGER NOT NULL, llm_frequency_penalty REAL NOT NULL,
			llm_presence_penalty REAL NOT NULL, slow_request_warning_seconds INTEGER NOT NULL,
			allow_llm_data_samples INTEGER NOT NULL, ollama_base_url TEXT NOT NULL,
			provider_catalogs_json TEXT NOT NULL,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
	}
	for _, statement := range statements {
		if _, err := db.Exec(statement); err != nil {
			t.Fatal(err)
		}
	}
	catalogs, err := json.Marshal(defaultCatalogs())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(`INSERT INTO model_preferences VALUES (
		1, 'openrouter', 'google/gemini-2.5-flash', 'google/gemini-2.5-flash-lite',
		'google/gemini-2.5-flash', 0.7, 4096, 1, 0, 0, 0, 120, 0,
		'http://localhost:11434', ?, CURRENT_TIMESTAMP
	)`, string(catalogs)); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	repository, err := OpenSQLite(path)
	if err != nil {
		t.Fatalf("OpenSQLite() migration error = %v", err)
	}
	defer repository.Close()
	preferences, err := repository.Load(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if preferences.ModelOnboardingCompleted {
		t.Fatal("upgraded foundation database should require first-run onboarding")
	}
	var versionTwoCount int
	if err := repository.db.QueryRow(`SELECT COUNT(*) FROM schema_migrations WHERE version = 2`).Scan(&versionTwoCount); err != nil {
		t.Fatal(err)
	}
	if versionTwoCount != 1 {
		t.Fatalf("onboarding migration count = %d", versionTwoCount)
	}
}
