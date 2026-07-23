package workspace

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

var errNotFound = errors.New("workspace not found")

type SQLiteRepository struct {
	db *sql.DB
}

func OpenSQLite(path string) (*SQLiteRepository, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, fmt.Errorf("create settings directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open workspace database: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	for _, statement := range []string{`PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("configure workspace database: %w", err)
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
		return fmt.Errorf("begin workspace migration: %w", err)
	}
	defer tx.Rollback()

	statements := []string{
		`CREATE TABLE IF NOT EXISTS schema_migrations (
			version INTEGER PRIMARY KEY,
			applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS workspaces (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			name_normalized TEXT NOT NULL UNIQUE,
			schema_context TEXT NOT NULL DEFAULT '',
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS workspace_state (
			id INTEGER PRIMARY KEY CHECK (id = 1),
			active_workspace_id TEXT NULL REFERENCES workspaces(id) ON DELETE SET NULL
		)`,
		`INSERT OR IGNORE INTO workspace_state(id, active_workspace_id) VALUES (1, NULL)`,
		`CREATE TABLE IF NOT EXISTS workspace_ai_config (
			workspace_id TEXT PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
			provider_override TEXT NULL,
			main_model_override TEXT NULL,
			lite_model_override TEXT NULL,
			coding_model_override TEXT NULL,
			temperature_override REAL NULL,
			max_tokens_override INTEGER NULL,
			top_p_override REAL NULL,
			allow_llm_data_samples INTEGER NOT NULL DEFAULT 0,
			configuration_reviewed INTEGER NOT NULL DEFAULT 0,
			updated_at TEXT NOT NULL
		)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (3)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (8)`,
	}
	for _, statement := range statements {
		if _, err := tx.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("apply workspace migration: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit workspace migration: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) List(ctx context.Context) ([]Workspace, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT w.id, w.name, w.schema_context, w.created_at, w.updated_at,
		COALESCE(s.active_workspace_id = w.id, 0)
		FROM workspaces w CROSS JOIN workspace_state s
		WHERE s.id = 1
		ORDER BY w.updated_at DESC, w.created_at DESC`)
	if err != nil {
		return nil, fmt.Errorf("list workspaces: %w", err)
	}
	defer rows.Close()
	workspaces := make([]Workspace, 0)
	for rows.Next() {
		workspace, err := scanWorkspace(rows)
		if err != nil {
			return nil, err
		}
		workspaces = append(workspaces, workspace)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate workspaces: %w", err)
	}
	return workspaces, nil
}

func (r *SQLiteRepository) Get(ctx context.Context, id string) (Workspace, error) {
	row := r.db.QueryRowContext(ctx, `SELECT w.id, w.name, w.schema_context, w.created_at, w.updated_at,
		COALESCE(s.active_workspace_id = w.id, 0)
		FROM workspaces w CROSS JOIN workspace_state s
		WHERE s.id = 1 AND w.id = ?`, id)
	workspace, err := scanWorkspace(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Workspace{}, errNotFound
	}
	return workspace, err
}

func (r *SQLiteRepository) Create(ctx context.Context, workspace Workspace, normalizedName string) (Workspace, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return Workspace{}, fmt.Errorf("begin workspace creation: %w", err)
	}
	defer tx.Rollback()
	if _, err := tx.ExecContext(ctx, `INSERT INTO workspaces(
		id, name, name_normalized, schema_context, created_at, updated_at
	) VALUES (?, ?, ?, ?, ?, ?)`, workspace.ID, workspace.Name, normalizedName,
		workspace.SchemaContext, workspace.CreatedAt, workspace.UpdatedAt); err != nil {
		return Workspace{}, fmt.Errorf("insert workspace: %w", err)
	}
	var activeID sql.NullString
	if err := tx.QueryRowContext(ctx, `SELECT active_workspace_id FROM workspace_state WHERE id = 1`).Scan(&activeID); err != nil {
		return Workspace{}, fmt.Errorf("load active workspace: %w", err)
	}
	if !activeID.Valid || activeID.String == "" {
		if _, err := tx.ExecContext(ctx, `UPDATE workspace_state SET active_workspace_id = ? WHERE id = 1`, workspace.ID); err != nil {
			return Workspace{}, fmt.Errorf("activate first workspace: %w", err)
		}
		workspace.IsActive = true
	}
	if err := tx.Commit(); err != nil {
		return Workspace{}, fmt.Errorf("commit workspace creation: %w", err)
	}
	return workspace, nil
}

func (r *SQLiteRepository) Activate(ctx context.Context, id string) (Workspace, error) {
	result, err := r.db.ExecContext(ctx, `UPDATE workspace_state
		SET active_workspace_id = ?
		WHERE id = 1 AND EXISTS (SELECT 1 FROM workspaces WHERE id = ?)`, id, id)
	if err != nil {
		return Workspace{}, fmt.Errorf("activate workspace: %w", err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return Workspace{}, fmt.Errorf("inspect workspace activation: %w", err)
	}
	if affected == 0 {
		return Workspace{}, errNotFound
	}
	return r.Get(ctx, id)
}

func (r *SQLiteRepository) Update(ctx context.Context, id, name, normalizedName string, schemaContext *string, updatedAt time.Time) (Workspace, error) {
	var result sql.Result
	var err error
	if schemaContext == nil {
		result, err = r.db.ExecContext(ctx, `UPDATE workspaces SET name = ?, name_normalized = ?, updated_at = ? WHERE id = ?`,
			name, normalizedName, formatTime(updatedAt), id)
	} else {
		result, err = r.db.ExecContext(ctx, `UPDATE workspaces SET name = ?, name_normalized = ?, schema_context = ?, updated_at = ? WHERE id = ?`,
			name, normalizedName, *schemaContext, formatTime(updatedAt), id)
	}
	if err != nil {
		return Workspace{}, fmt.Errorf("update workspace: %w", err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return Workspace{}, fmt.Errorf("inspect workspace update: %w", err)
	}
	if affected == 0 {
		return Workspace{}, errNotFound
	}
	return r.Get(ctx, id)
}

func (r *SQLiteRepository) Delete(ctx context.Context, id string) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin workspace deletion: %w", err)
	}
	defer tx.Rollback()
	var wasActive bool
	if err := tx.QueryRowContext(ctx, `SELECT EXISTS(
		SELECT 1 FROM workspace_state WHERE id = 1 AND active_workspace_id = ?
	)`, id).Scan(&wasActive); err != nil {
		return fmt.Errorf("inspect active workspace: %w", err)
	}
	result, err := tx.ExecContext(ctx, `DELETE FROM workspaces WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete workspace: %w", err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("inspect workspace deletion: %w", err)
	}
	if affected == 0 {
		return errNotFound
	}
	if wasActive {
		var fallbackID sql.NullString
		if err := tx.QueryRowContext(ctx, `SELECT id FROM workspaces ORDER BY updated_at DESC, created_at DESC LIMIT 1`).Scan(&fallbackID); err != nil && !errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("select fallback workspace: %w", err)
		}
		if _, err := tx.ExecContext(ctx, `UPDATE workspace_state SET active_workspace_id = ? WHERE id = 1`, fallbackID); err != nil {
			return fmt.Errorf("activate fallback workspace: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit workspace deletion: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) GetAIConfig(ctx context.Context, workspaceID string) (aiConfigRecord, error) {
	row := r.db.QueryRowContext(ctx, `SELECT w.id,
		c.provider_override, c.main_model_override, c.lite_model_override, c.coding_model_override,
		c.temperature_override, c.max_tokens_override, c.top_p_override,
		COALESCE(c.allow_llm_data_samples, 0), COALESCE(c.configuration_reviewed, 0)
		FROM workspaces w LEFT JOIN workspace_ai_config c ON c.workspace_id = w.id
		WHERE w.id = ?`, workspaceID)
	var record aiConfigRecord
	var provider, mainModel, liteModel, codingModel sql.NullString
	var temperature, topP sql.NullFloat64
	var maxTokens sql.NullInt64
	if err := row.Scan(
		&record.WorkspaceID, &provider, &mainModel, &liteModel, &codingModel,
		&temperature, &maxTokens, &topP, &record.AllowDataSamples, &record.ConfigurationReviewed,
	); errors.Is(err, sql.ErrNoRows) {
		return aiConfigRecord{}, errNotFound
	} else if err != nil {
		return aiConfigRecord{}, err
	}
	record.Provider = nullStringPointer(provider)
	record.MainModel = nullStringPointer(mainModel)
	record.LiteModel = nullStringPointer(liteModel)
	record.CodingModel = nullStringPointer(codingModel)
	record.Temperature = nullFloatPointer(temperature)
	record.MaxTokens = nullIntPointer(maxTokens)
	record.TopP = nullFloatPointer(topP)
	return record, nil
}

func (r *SQLiteRepository) SaveAIConfig(ctx context.Context, record aiConfigRecord, updatedAt string) error {
	_, err := r.db.ExecContext(ctx, `INSERT INTO workspace_ai_config(
		workspace_id, provider_override, main_model_override, lite_model_override, coding_model_override,
		temperature_override, max_tokens_override, top_p_override,
		allow_llm_data_samples, configuration_reviewed, updated_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	ON CONFLICT(workspace_id) DO UPDATE SET
		provider_override=excluded.provider_override,
		main_model_override=excluded.main_model_override,
		lite_model_override=excluded.lite_model_override,
		coding_model_override=excluded.coding_model_override,
		temperature_override=excluded.temperature_override,
		max_tokens_override=excluded.max_tokens_override,
		top_p_override=excluded.top_p_override,
		allow_llm_data_samples=excluded.allow_llm_data_samples,
		configuration_reviewed=excluded.configuration_reviewed,
		updated_at=excluded.updated_at`,
		record.WorkspaceID, record.Provider, record.MainModel, record.LiteModel, record.CodingModel,
		record.Temperature, record.MaxTokens, record.TopP,
		record.AllowDataSamples, record.ConfigurationReviewed, updatedAt,
	)
	return err
}

func (r *SQLiteRepository) Close() error { return r.db.Close() }

type scanner interface {
	Scan(...any) error
}

func scanWorkspace(row scanner) (Workspace, error) {
	var workspace Workspace
	if err := row.Scan(&workspace.ID, &workspace.Name, &workspace.SchemaContext, &workspace.CreatedAt, &workspace.UpdatedAt, &workspace.IsActive); err != nil {
		return Workspace{}, err
	}
	return workspace, nil
}

func nullStringPointer(value sql.NullString) *string {
	if !value.Valid {
		return nil
	}
	result := value.String
	return &result
}

func nullFloatPointer(value sql.NullFloat64) *float64 {
	if !value.Valid {
		return nil
	}
	result := value.Float64
	return &result
}

func nullIntPointer(value sql.NullInt64) *int {
	if !value.Valid {
		return nil
	}
	result := int(value.Int64)
	return &result
}

func formatTime(value time.Time) string { return value.UTC().Format(time.RFC3339Nano) }
