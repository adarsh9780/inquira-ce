package connection

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

var errNotFound = errors.New("connection not found")

type SQLiteRepository struct {
	db *sql.DB
}

func OpenSQLite(path string) (*SQLiteRepository, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, fmt.Errorf("create settings directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open connection database: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	for _, statement := range []string{`PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("configure connection database: %w", err)
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
		return fmt.Errorf("begin connection migration: %w", err)
	}
	defer tx.Rollback()
	statements := []string{
		`CREATE TABLE IF NOT EXISTS connections (
			id TEXT PRIMARY KEY,
			workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
			name TEXT NOT NULL,
			name_normalized TEXT NOT NULL,
			adapter_kind TEXT NOT NULL,
			source_path TEXT NOT NULL,
			source_fingerprint TEXT NOT NULL,
			status TEXT NOT NULL,
			error_message TEXT NOT NULL DEFAULT '',
			selected_object_ids_json TEXT NOT NULL,
			options_json TEXT NOT NULL,
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL,
			last_refresh_attempt_at TEXT NOT NULL,
			last_refresh_success_at TEXT NOT NULL,
			UNIQUE(workspace_id, name_normalized)
		)`,
		`CREATE TABLE IF NOT EXISTS connection_outputs (
			id TEXT PRIMARY KEY,
			connection_id TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
			source_object_id TEXT NOT NULL,
			name TEXT NOT NULL,
			snapshot_path TEXT NOT NULL,
			format TEXT NOT NULL,
			columns_json TEXT NOT NULL,
			row_count INTEGER NOT NULL,
			byte_size INTEGER NOT NULL,
			UNIQUE(connection_id, source_object_id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_connections_workspace ON connections(workspace_id)`,
		`INSERT OR IGNORE INTO schema_migrations(version) VALUES (4)`,
	}
	for _, statement := range statements {
		if _, err := tx.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("apply connection migration: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit connection migration: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) WorkspaceExists(ctx context.Context, workspaceID string) (bool, error) {
	var exists bool
	err := r.db.QueryRowContext(ctx, `SELECT EXISTS(SELECT 1 FROM workspaces WHERE id = ?)`, workspaceID).Scan(&exists)
	return exists, err
}

func (r *SQLiteRepository) Create(ctx context.Context, connection Connection, normalizedName string) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	selected, err := json.Marshal(connection.SelectedObjectIDs)
	if err != nil {
		return err
	}
	options, err := json.Marshal(connection.Options)
	if err != nil {
		return err
	}
	_, err = tx.ExecContext(ctx, `INSERT INTO connections(
		id, workspace_id, name, name_normalized, adapter_kind, source_path,
		source_fingerprint, status, error_message, selected_object_ids_json, options_json,
		created_at, updated_at, last_refresh_attempt_at, last_refresh_success_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		connection.ID, connection.WorkspaceID, connection.Name, normalizedName,
		connection.AdapterKind, connection.SourcePath, connection.SourceFingerprint,
		connection.Status, connection.ErrorMessage, string(selected), string(options), connection.CreatedAt,
		connection.UpdatedAt, connection.LastRefreshAttemptAt, connection.LastRefreshSuccessAt)
	if err != nil {
		return err
	}
	if err := insertOutputs(ctx, tx, connection.Outputs); err != nil {
		return err
	}
	return tx.Commit()
}

func (r *SQLiteRepository) Get(ctx context.Context, id string) (Connection, error) {
	connection, err := scanConnection(r.db.QueryRowContext(ctx, `SELECT
		id, workspace_id, name, adapter_kind, source_path, source_fingerprint,
		status, error_message, selected_object_ids_json, options_json, created_at, updated_at,
		last_refresh_attempt_at, last_refresh_success_at
		FROM connections WHERE id = ?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		return Connection{}, errNotFound
	}
	if err != nil {
		return Connection{}, err
	}
	connection.Outputs, err = r.outputs(ctx, id)
	return connection, err
}

func (r *SQLiteRepository) List(ctx context.Context, workspaceID string) ([]Connection, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT
		id, workspace_id, name, adapter_kind, source_path, source_fingerprint,
		status, error_message, selected_object_ids_json, options_json, created_at, updated_at,
		last_refresh_attempt_at, last_refresh_success_at
		FROM connections WHERE workspace_id = ? ORDER BY updated_at DESC, created_at DESC`, workspaceID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	connections := make([]Connection, 0)
	for rows.Next() {
		connection, err := scanConnection(rows)
		if err != nil {
			return nil, err
		}
		connections = append(connections, connection)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	for index := range connections {
		connections[index].Outputs, err = r.outputs(ctx, connections[index].ID)
		if err != nil {
			return nil, err
		}
	}
	return connections, nil
}

func (r *SQLiteRepository) ReplaceSnapshot(ctx context.Context, connection Connection) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	result, err := tx.ExecContext(ctx, `UPDATE connections SET
		source_fingerprint = ?, status = ?, error_message = '', updated_at = ?,
		last_refresh_attempt_at = ?, last_refresh_success_at = ? WHERE id = ?`,
		connection.SourceFingerprint, StatusReady, connection.UpdatedAt,
		connection.LastRefreshAttemptAt, connection.LastRefreshSuccessAt, connection.ID)
	if err != nil {
		return err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return errNotFound
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM connection_outputs WHERE connection_id = ?`, connection.ID); err != nil {
		return err
	}
	if err := insertOutputs(ctx, tx, connection.Outputs); err != nil {
		return err
	}
	return tx.Commit()
}

func (r *SQLiteRepository) MarkReady(ctx context.Context, id, timestamp string) error {
	result, err := r.db.ExecContext(ctx, `UPDATE connections SET status = ?, error_message = '',
		updated_at = ?, last_refresh_attempt_at = ? WHERE id = ?`, StatusReady, timestamp, timestamp, id)
	if err == nil {
		if affected, _ := result.RowsAffected(); affected == 0 {
			return errNotFound
		}
	}
	return err
}

func (r *SQLiteRepository) MarkRefreshing(ctx context.Context, id, timestamp string) error {
	result, err := r.db.ExecContext(ctx, `UPDATE connections SET status = ?, error_message = '',
		updated_at = ?, last_refresh_attempt_at = ? WHERE id = ?`, StatusRefreshing, timestamp, timestamp, id)
	if err == nil {
		if affected, _ := result.RowsAffected(); affected == 0 {
			return errNotFound
		}
	}
	return err
}

func (r *SQLiteRepository) MarkNeedsAttention(ctx context.Context, id, message, timestamp string) error {
	result, err := r.db.ExecContext(ctx, `UPDATE connections SET status = ?, error_message = ?,
		updated_at = ?, last_refresh_attempt_at = ? WHERE id = ?`, StatusNeedsAttention, message, timestamp, timestamp, id)
	if err == nil {
		if affected, _ := result.RowsAffected(); affected == 0 {
			return errNotFound
		}
	}
	return err
}

func (r *SQLiteRepository) MarkError(ctx context.Context, id, message, timestamp string) error {
	result, err := r.db.ExecContext(ctx, `UPDATE connections SET status = ?, error_message = ?,
		updated_at = ?, last_refresh_attempt_at = ? WHERE id = ?`, StatusError, message, timestamp, timestamp, id)
	if err == nil {
		if affected, _ := result.RowsAffected(); affected == 0 {
			return errNotFound
		}
	}
	return err
}

func (r *SQLiteRepository) Delete(ctx context.Context, id string) error {
	result, err := r.db.ExecContext(ctx, `DELETE FROM connections WHERE id = ?`, id)
	if err != nil {
		return err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return errNotFound
	}
	return nil
}

func (r *SQLiteRepository) outputs(ctx context.Context, connectionID string) ([]Output, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT id, connection_id, source_object_id, name,
		snapshot_path, format, columns_json, row_count, byte_size
		FROM connection_outputs WHERE connection_id = ? ORDER BY name, id`, connectionID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	outputs := make([]Output, 0)
	for rows.Next() {
		var output Output
		var columns string
		if err := rows.Scan(&output.ID, &output.ConnectionID, &output.SourceObjectID,
			&output.Name, &output.SnapshotPath, &output.Format, &columns,
			&output.RowCount, &output.ByteSize); err != nil {
			return nil, err
		}
		if err := json.Unmarshal([]byte(columns), &output.Columns); err != nil {
			return nil, err
		}
		outputs = append(outputs, output)
	}
	return outputs, rows.Err()
}

func (r *SQLiteRepository) Close() error { return r.db.Close() }

type rowScanner interface{ Scan(...any) error }

func scanConnection(row rowScanner) (Connection, error) {
	var connection Connection
	var selected, options string
	if err := row.Scan(&connection.ID, &connection.WorkspaceID, &connection.Name,
		&connection.AdapterKind, &connection.SourcePath, &connection.SourceFingerprint,
		&connection.Status, &connection.ErrorMessage, &selected, &options, &connection.CreatedAt,
		&connection.UpdatedAt, &connection.LastRefreshAttemptAt,
		&connection.LastRefreshSuccessAt); err != nil {
		return Connection{}, err
	}
	if err := json.Unmarshal([]byte(selected), &connection.SelectedObjectIDs); err != nil {
		return Connection{}, err
	}
	if err := json.Unmarshal([]byte(options), &connection.Options); err != nil {
		return Connection{}, err
	}
	connection.Outputs = []Output{}
	return connection, nil
}

func insertOutputs(ctx context.Context, tx *sql.Tx, outputs []Output) error {
	for _, output := range outputs {
		columns, err := json.Marshal(output.Columns)
		if err != nil {
			return err
		}
		_, err = tx.ExecContext(ctx, `INSERT INTO connection_outputs(
			id, connection_id, source_object_id, name, snapshot_path, format,
			columns_json, row_count, byte_size
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`, output.ID, output.ConnectionID,
			output.SourceObjectID, output.Name, output.SnapshotPath, output.Format,
			string(columns), output.RowCount, output.ByteSize)
		if err != nil {
			return err
		}
	}
	return nil
}
