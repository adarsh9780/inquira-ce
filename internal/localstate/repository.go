package localstate

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	_ "modernc.org/sqlite"
)

const defaultScope = "default"

type Snapshot = map[string]any

type Repository interface {
	Save(context.Context, string, Snapshot) error
	Load(context.Context, string) (Snapshot, bool, error)
	Close() error
}

type SQLiteRepository struct {
	db *sql.DB
}

func OpenSQLite(path string) (*SQLiteRepository, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, fmt.Errorf("create local state directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open local state database: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	for _, statement := range []string{`PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("configure local state database: %w", err)
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
		return fmt.Errorf("begin local state migration: %w", err)
	}
	defer tx.Rollback()
	for _, statement := range []string{
		`CREATE TABLE IF NOT EXISTS schema_migrations (
			version INTEGER PRIMARY KEY,
			applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS local_state_snapshots (
			scope TEXT PRIMARY KEY,
			snapshot_json TEXT NOT NULL,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (9)`,
	} {
		if _, err := tx.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("apply local state migration: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit local state migration: %w", err)
	}
	return nil
}

func NormalizeScope(scope string) string {
	raw := strings.ToLower(strings.TrimSpace(scope))
	if raw == "" {
		return defaultScope
	}
	var normalized strings.Builder
	for _, character := range raw {
		if (character >= 'a' && character <= 'z') || (character >= '0' && character <= '9') || character == '_' || character == '-' {
			normalized.WriteRune(character)
		} else {
			normalized.WriteByte('_')
		}
	}
	if normalized.Len() == 0 {
		return defaultScope
	}
	return normalized.String()
}

func (r *SQLiteRepository) Save(ctx context.Context, scope string, snapshot Snapshot) error {
	if snapshot == nil {
		return errors.New("local state snapshot is required")
	}
	payload, err := json.Marshal(snapshot)
	if err != nil {
		return fmt.Errorf("encode local state snapshot: %w", err)
	}
	_, err = r.db.ExecContext(ctx, `INSERT INTO local_state_snapshots(scope, snapshot_json, updated_at)
		VALUES (?, ?, CURRENT_TIMESTAMP)
		ON CONFLICT(scope) DO UPDATE SET snapshot_json = excluded.snapshot_json, updated_at = CURRENT_TIMESTAMP`,
		NormalizeScope(scope), string(payload))
	if err != nil {
		return fmt.Errorf("save local state snapshot: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) Load(ctx context.Context, scope string) (Snapshot, bool, error) {
	var payload string
	err := r.db.QueryRowContext(ctx, `SELECT snapshot_json FROM local_state_snapshots WHERE scope = ?`, NormalizeScope(scope)).Scan(&payload)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, fmt.Errorf("load local state snapshot: %w", err)
	}
	var snapshot Snapshot
	if err := json.Unmarshal([]byte(payload), &snapshot); err != nil {
		return nil, false, fmt.Errorf("decode local state snapshot: %w", err)
	}
	if snapshot == nil {
		return nil, false, errors.New("decode local state snapshot: expected an object")
	}
	return snapshot, true, nil
}

func (r *SQLiteRepository) Close() error { return r.db.Close() }
