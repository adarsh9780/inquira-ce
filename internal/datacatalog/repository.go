package datacatalog

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

type SQLiteRepository struct {
	db *sql.DB
}

func OpenSQLite(path string) (*SQLiteRepository, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, fmt.Errorf("create schema directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open schema database: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	for _, statement := range []string{`PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("configure schema database: %w", err)
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
		return fmt.Errorf("begin schema migration: %w", err)
	}
	defer tx.Rollback()
	for _, statement := range []string{
		`CREATE TABLE IF NOT EXISTS dataset_schema_columns (
			workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
			table_name TEXT NOT NULL,
			column_name TEXT NOT NULL,
			description TEXT NOT NULL DEFAULT '',
			aliases_json TEXT NOT NULL DEFAULT '[]',
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY(workspace_id, table_name, column_name)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_dataset_schema_workspace_table ON dataset_schema_columns(workspace_id, table_name)`,
		`CREATE TABLE IF NOT EXISTS dataset_schema_tables (
			workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
			table_name TEXT NOT NULL,
			context TEXT NOT NULL DEFAULT '',
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY(workspace_id, table_name)
		)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (7)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (10)`,
	} {
		if _, err := tx.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("apply schema migration: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit schema migration: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) List(ctx context.Context, workspaceID, tableName string) ([]ColumnOverride, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT column_name, description, aliases_json
		FROM dataset_schema_columns WHERE workspace_id = ? AND table_name = ? ORDER BY rowid`, workspaceID, tableName)
	if err != nil {
		return nil, fmt.Errorf("list schema overrides: %w", err)
	}
	defer rows.Close()
	result := make([]ColumnOverride, 0)
	for rows.Next() {
		var item ColumnOverride
		var aliasesJSON string
		if err := rows.Scan(&item.Name, &item.Description, &aliasesJSON); err != nil {
			return nil, fmt.Errorf("scan schema override: %w", err)
		}
		if err := json.Unmarshal([]byte(aliasesJSON), &item.Aliases); err != nil {
			return nil, fmt.Errorf("decode schema aliases: %w", err)
		}
		result = append(result, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate schema overrides: %w", err)
	}
	return result, nil
}

func (r *SQLiteRepository) TableContext(ctx context.Context, workspaceID, tableName string) (string, error) {
	var value string
	err := r.db.QueryRowContext(ctx, `SELECT context FROM dataset_schema_tables WHERE workspace_id = ? AND table_name = ?`, workspaceID, tableName).Scan(&value)
	if err == sql.ErrNoRows {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("read table context: %w", err)
	}
	return value, nil
}

func (r *SQLiteRepository) Replace(ctx context.Context, workspaceID, tableName string, tableContext *string, items []ColumnOverride) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin schema replacement: %w", err)
	}
	defer tx.Rollback()
	if tableContext != nil {
		if _, err := tx.ExecContext(ctx, `INSERT INTO dataset_schema_tables(workspace_id, table_name, context)
			VALUES (?, ?, ?) ON CONFLICT(workspace_id, table_name) DO UPDATE SET context = excluded.context, updated_at = CURRENT_TIMESTAMP`, workspaceID, tableName, *tableContext); err != nil {
			return fmt.Errorf("save table context: %w", err)
		}
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM dataset_schema_columns WHERE workspace_id = ? AND table_name = ?`, workspaceID, tableName); err != nil {
		return fmt.Errorf("clear schema overrides: %w", err)
	}
	for _, item := range items {
		aliases, err := json.Marshal(item.Aliases)
		if err != nil {
			return fmt.Errorf("encode schema aliases: %w", err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO dataset_schema_columns(
			workspace_id, table_name, column_name, description, aliases_json
		) VALUES (?, ?, ?, ?, ?)`, workspaceID, tableName, item.Name, item.Description, string(aliases)); err != nil {
			return fmt.Errorf("insert schema override: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit schema replacement: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) Close() error { return r.db.Close() }
