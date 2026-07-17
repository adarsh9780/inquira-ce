package modelconfig

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

type Repository interface {
	Load(context.Context) (Preferences, error)
	Save(context.Context, Preferences) error
	Close() error
}

type SQLiteRepository struct {
	db *sql.DB
}

func OpenSQLite(path string) (*SQLiteRepository, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, fmt.Errorf("create settings directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open settings database: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	for _, statement := range []string{`PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("configure settings database: %w", err)
		}
	}
	repository := &SQLiteRepository{db: db}
	if err := repository.migrate(context.Background()); err != nil {
		_ = db.Close()
		return nil, err
	}
	return repository, nil
}

func (r *SQLiteRepository) migrate(ctx context.Context) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin settings migration: %w", err)
	}
	defer tx.Rollback()

	statements := []string{
		`CREATE TABLE IF NOT EXISTS schema_migrations (
			version INTEGER PRIMARY KEY,
			applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS model_preferences (
			id INTEGER PRIMARY KEY CHECK (id = 1),
			llm_provider TEXT NOT NULL,
			selected_model TEXT NOT NULL,
			selected_lite_model TEXT NOT NULL,
			selected_coding_model TEXT NOT NULL,
			llm_temperature REAL NOT NULL,
			llm_max_tokens INTEGER NOT NULL,
			llm_top_p REAL NOT NULL,
			llm_top_k INTEGER NOT NULL,
			llm_frequency_penalty REAL NOT NULL,
			llm_presence_penalty REAL NOT NULL,
			slow_request_warning_seconds INTEGER NOT NULL,
			allow_llm_data_samples INTEGER NOT NULL,
			ollama_base_url TEXT NOT NULL,
			provider_catalogs_json TEXT NOT NULL,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (1)`,
	}
	for _, statement := range statements {
		if _, err := tx.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("apply settings migration: %w", err)
		}
	}
	var onboardingMigrationApplied bool
	if err := tx.QueryRowContext(ctx, `SELECT EXISTS(
		SELECT 1 FROM schema_migrations WHERE version = 2
	)`).Scan(&onboardingMigrationApplied); err != nil {
		return fmt.Errorf("inspect onboarding migration: %w", err)
	}
	if !onboardingMigrationApplied {
		if _, err := tx.ExecContext(ctx, `ALTER TABLE model_preferences
			ADD COLUMN model_onboarding_completed INTEGER NOT NULL DEFAULT 0`); err != nil {
			return fmt.Errorf("add model onboarding preference: %w", err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO schema_migrations(version) VALUES (2)`); err != nil {
			return fmt.Errorf("record onboarding migration: %w", err)
		}
	}

	defaults := defaultPreferences()
	catalogs, err := json.Marshal(defaults.Catalogs)
	if err != nil {
		return fmt.Errorf("encode default provider catalogs: %w", err)
	}
	_, err = tx.ExecContext(ctx, `INSERT OR IGNORE INTO model_preferences (
		id, llm_provider, selected_model, selected_lite_model, selected_coding_model,
		llm_temperature, llm_max_tokens, llm_top_p, llm_top_k,
		llm_frequency_penalty, llm_presence_penalty, slow_request_warning_seconds,
		allow_llm_data_samples, ollama_base_url, provider_catalogs_json
	) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		defaults.LLMProvider, defaults.SelectedModel, defaults.SelectedLiteModel,
		defaults.SelectedCodingModel, defaults.Temperature, defaults.MaxTokens,
		defaults.TopP, defaults.TopK, defaults.FrequencyPenalty,
		defaults.PresencePenalty, defaults.SlowRequestWarningSeconds,
		defaults.AllowLLMDataSamples, defaults.OllamaBaseURL, string(catalogs),
	)
	if err != nil {
		return fmt.Errorf("insert default model preferences: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit settings migration: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) Load(ctx context.Context) (Preferences, error) {
	var preferences Preferences
	var catalogsJSON string
	err := r.db.QueryRowContext(ctx, `SELECT
		llm_provider, selected_model, selected_lite_model, selected_coding_model,
		llm_temperature, llm_max_tokens, llm_top_p, llm_top_k,
		llm_frequency_penalty, llm_presence_penalty, slow_request_warning_seconds,
		allow_llm_data_samples, model_onboarding_completed, ollama_base_url, provider_catalogs_json
		FROM model_preferences WHERE id = 1`).Scan(
		&preferences.LLMProvider, &preferences.SelectedModel,
		&preferences.SelectedLiteModel, &preferences.SelectedCodingModel,
		&preferences.Temperature, &preferences.MaxTokens, &preferences.TopP,
		&preferences.TopK, &preferences.FrequencyPenalty,
		&preferences.PresencePenalty, &preferences.SlowRequestWarningSeconds,
		&preferences.AllowLLMDataSamples, &preferences.ModelOnboardingCompleted,
		&preferences.OllamaBaseURL, &catalogsJSON,
	)
	if err != nil {
		return Preferences{}, fmt.Errorf("load model preferences: %w", err)
	}
	var catalogs map[string]Catalog
	if err := json.Unmarshal([]byte(catalogsJSON), &catalogs); err != nil {
		return Preferences{}, fmt.Errorf("decode provider catalogs: %w", err)
	}
	preferences.Catalogs = mergeCatalogs(catalogs)
	return preferences, nil
}

func (r *SQLiteRepository) Save(ctx context.Context, preferences Preferences) error {
	catalogs, err := json.Marshal(preferences.Catalogs)
	if err != nil {
		return fmt.Errorf("encode provider catalogs: %w", err)
	}
	_, err = r.db.ExecContext(ctx, `UPDATE model_preferences SET
		llm_provider = ?, selected_model = ?, selected_lite_model = ?, selected_coding_model = ?,
		llm_temperature = ?, llm_max_tokens = ?, llm_top_p = ?, llm_top_k = ?,
		llm_frequency_penalty = ?, llm_presence_penalty = ?, slow_request_warning_seconds = ?,
		allow_llm_data_samples = ?, model_onboarding_completed = ?,
		ollama_base_url = ?, provider_catalogs_json = ?,
		updated_at = CURRENT_TIMESTAMP WHERE id = 1`,
		preferences.LLMProvider, preferences.SelectedModel, preferences.SelectedLiteModel,
		preferences.SelectedCodingModel, preferences.Temperature, preferences.MaxTokens,
		preferences.TopP, preferences.TopK, preferences.FrequencyPenalty,
		preferences.PresencePenalty, preferences.SlowRequestWarningSeconds,
		preferences.AllowLLMDataSamples, preferences.ModelOnboardingCompleted,
		preferences.OllamaBaseURL, string(catalogs),
	)
	if err != nil {
		return fmt.Errorf("save model preferences: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) Close() error { return r.db.Close() }

func defaultPreferences() Preferences {
	catalogs := defaultCatalogs()
	selected := catalogs["openrouter"]
	return Preferences{
		LLMProvider: "openrouter", SelectedModel: selected.DefaultMainModel,
		SelectedLiteModel: selected.DefaultLiteModel, SelectedCodingModel: selected.DefaultMainModel,
		Temperature: 0.7, MaxTokens: 4096, TopP: 1, TopK: 0,
		FrequencyPenalty: 0, PresencePenalty: 0, SlowRequestWarningSeconds: 120,
		OllamaBaseURL: "http://localhost:11434", Catalogs: catalogs,
	}
}
