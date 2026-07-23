package conversation

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

var (
	errConversationNotFound = errors.New("conversation not found")
	errTurnNotFound         = errors.New("turn not found")
	errParentTurnNotFound   = errors.New("parent turn not found")
	errArtifactNotFound     = errors.New("artifact not found")
	errTurnStateInvalid     = errors.New("turn state does not allow this operation")
	errTurnNotLeaf          = errors.New("turn is not a leaf")
)

type SQLiteRepository struct {
	db *sql.DB
}

func OpenSQLite(path string) (*SQLiteRepository, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, fmt.Errorf("create settings directory: %w", err)
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open conversation database: %w", err)
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	for _, statement := range []string{`PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			return nil, fmt.Errorf("configure conversation database: %w", err)
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
	hasFinalTurnID, err := r.hasColumn(ctx, "conversations", "final_turn_id")
	if err != nil {
		return err
	}
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin conversation migration: %w", err)
	}
	defer tx.Rollback()
	statements := []string{
		`CREATE TABLE IF NOT EXISTS conversations (
			id TEXT PRIMARY KEY,
			workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
			title TEXT NOT NULL,
			status TEXT NOT NULL,
			next_turn_sequence INTEGER NOT NULL DEFAULT 1,
			last_turn_at TEXT NOT NULL DEFAULT '',
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS turns (
			id TEXT PRIMARY KEY,
			conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
			parent_turn_id TEXT NULL REFERENCES turns(id) ON DELETE SET NULL,
			sequence INTEGER NOT NULL,
			sibling_order INTEGER NOT NULL DEFAULT 0,
			status TEXT NOT NULL,
			result_kind TEXT NOT NULL DEFAULT '',
			user_text TEXT NOT NULL,
			assistant_text TEXT NOT NULL DEFAULT '',
			tool_events_json TEXT NOT NULL DEFAULT '[]',
			metadata_json TEXT NOT NULL DEFAULT '{}',
			code_snapshot TEXT NOT NULL DEFAULT '',
			result_json TEXT NOT NULL DEFAULT '',
			error_message TEXT NOT NULL DEFAULT '',
			created_at TEXT NOT NULL,
			updated_at TEXT NOT NULL,
			UNIQUE(conversation_id, sequence)
		)`,
		`CREATE TABLE IF NOT EXISTS artifacts (
			id TEXT PRIMARY KEY,
			workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
			conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
			turn_id TEXT NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
			kind TEXT NOT NULL,
			logical_name TEXT NOT NULL,
			display_name TEXT NOT NULL DEFAULT '',
			storage_class TEXT NOT NULL,
			relative_path TEXT NOT NULL,
			payload_format TEXT NOT NULL,
			media_type TEXT NOT NULL DEFAULT '',
			byte_size INTEGER NOT NULL,
			sha256 TEXT NOT NULL,
			status TEXT NOT NULL,
			created_at TEXT NOT NULL,
			UNIQUE(workspace_id, relative_path)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_conversations_workspace_updated ON conversations(workspace_id, status, updated_at DESC)`,
		`CREATE INDEX IF NOT EXISTS idx_turns_conversation_sequence ON turns(conversation_id, sequence)`,
		`CREATE INDEX IF NOT EXISTS idx_turns_parent ON turns(parent_turn_id, sibling_order)`,
		`CREATE INDEX IF NOT EXISTS idx_artifacts_turn_created ON artifacts(turn_id, created_at, id)`,
		`CREATE INDEX IF NOT EXISTS idx_artifacts_conversation_status ON artifacts(conversation_id, status)`,
	}
	if !hasFinalTurnID {
		statements = append(statements, `ALTER TABLE conversations ADD COLUMN final_turn_id TEXT NULL`)
	}
	statements = append(statements, `INSERT OR IGNORE INTO schema_migrations(version) VALUES (6)`)
	for _, statement := range statements {
		if _, err := tx.ExecContext(ctx, statement); err != nil {
			return fmt.Errorf("apply conversation migration: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit conversation migration: %w", err)
	}
	return nil
}

func (r *SQLiteRepository) hasColumn(ctx context.Context, table, column string) (bool, error) {
	rows, err := r.db.QueryContext(ctx, `PRAGMA table_info(`+table+`)`)
	if err != nil {
		return false, fmt.Errorf("inspect conversation schema: %w", err)
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, dataType string
		var notNull, primaryKey int
		var defaultValue any
		if err := rows.Scan(&cid, &name, &dataType, &notNull, &defaultValue, &primaryKey); err != nil {
			return false, err
		}
		if name == column {
			return true, nil
		}
	}
	return false, rows.Err()
}

func (r *SQLiteRepository) WorkspaceExists(ctx context.Context, workspaceID string) (bool, error) {
	var exists bool
	err := r.db.QueryRowContext(ctx, `SELECT EXISTS(SELECT 1 FROM workspaces WHERE id = ?)`, workspaceID).Scan(&exists)
	return exists, err
}

func (r *SQLiteRepository) CreateConversation(ctx context.Context, conversation Conversation) error {
	_, err := r.db.ExecContext(ctx, `INSERT INTO conversations(
		id, workspace_id, title, status, created_at, updated_at
	) VALUES (?, ?, ?, ?, ?, ?)`, conversation.ID, conversation.WorkspaceID, conversation.Title,
		conversation.Status, conversation.CreatedAt, conversation.UpdatedAt)
	return err
}

func (r *SQLiteRepository) GetConversation(ctx context.Context, id string, includeDeleting bool) (Conversation, error) {
	query := `SELECT id, workspace_id, title, status, final_turn_id, last_turn_at, created_at, updated_at FROM conversations WHERE id = ?`
	if !includeDeleting {
		query += ` AND status = 'active'`
	}
	conversation, err := scanConversation(r.db.QueryRowContext(ctx, query, id))
	if errors.Is(err, sql.ErrNoRows) {
		return Conversation{}, errConversationNotFound
	}
	return conversation, err
}

func (r *SQLiteRepository) ListConversations(ctx context.Context, workspaceID string, includeDeleting bool) ([]Conversation, error) {
	query := `SELECT id, workspace_id, title, status, final_turn_id, last_turn_at, created_at, updated_at
		FROM conversations WHERE workspace_id = ?`
	if !includeDeleting {
		query += ` AND status = 'active'`
	}
	query += ` ORDER BY updated_at DESC, created_at DESC, id`
	rows, err := r.db.QueryContext(ctx, query, workspaceID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := make([]Conversation, 0)
	for rows.Next() {
		conversation, err := scanConversation(rows)
		if err != nil {
			return nil, err
		}
		result = append(result, conversation)
	}
	return result, rows.Err()
}

func (r *SQLiteRepository) UpdateConversationTitle(ctx context.Context, id, title, updatedAt string) (Conversation, error) {
	result, err := r.db.ExecContext(ctx, `UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND status = ?`, title, updatedAt, id, ConversationStatusActive)
	if err != nil {
		return Conversation{}, err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return Conversation{}, errConversationNotFound
	}
	return r.GetConversation(ctx, id, false)
}

func (r *SQLiteRepository) WorkspaceIDs(ctx context.Context) ([]string, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT id FROM workspaces ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := make([]string, 0)
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		result = append(result, id)
	}
	return result, rows.Err()
}

func (r *SQLiteRepository) MarkConversationDeleting(ctx context.Context, id, updatedAt string) error {
	result, err := r.db.ExecContext(ctx, `UPDATE conversations SET status = ?, updated_at = ? WHERE id = ? AND status = ?`,
		ConversationStatusDeleting, updatedAt, id, ConversationStatusActive)
	if err != nil {
		return err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return errConversationNotFound
	}
	return nil
}

func (r *SQLiteRepository) PurgeConversation(ctx context.Context, id string) error {
	result, err := r.db.ExecContext(ctx, `DELETE FROM conversations WHERE id = ?`, id)
	if err != nil {
		return err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return errConversationNotFound
	}
	return nil
}

func (r *SQLiteRepository) CreateTurn(ctx context.Context, turn Turn) (Turn, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return Turn{}, err
	}
	defer tx.Rollback()
	var nextSequence int
	if err := tx.QueryRowContext(ctx, `SELECT next_turn_sequence FROM conversations WHERE id = ? AND status = ?`,
		turn.ConversationID, ConversationStatusActive).Scan(&nextSequence); errors.Is(err, sql.ErrNoRows) {
		return Turn{}, errConversationNotFound
	} else if err != nil {
		return Turn{}, err
	}
	if turn.ParentTurnID != nil {
		var parentConversationID string
		if err := tx.QueryRowContext(ctx, `SELECT conversation_id FROM turns WHERE id = ?`, *turn.ParentTurnID).Scan(&parentConversationID); errors.Is(err, sql.ErrNoRows) || parentConversationID != turn.ConversationID {
			return Turn{}, errParentTurnNotFound
		} else if err != nil {
			return Turn{}, err
		}
	}
	if _, err := tx.ExecContext(ctx, `UPDATE conversations SET final_turn_id = NULL WHERE id = ? AND final_turn_id IS ?`, turn.ConversationID, turn.ParentTurnID); err != nil {
		return Turn{}, err
	}
	var siblingOrder int
	if err := tx.QueryRowContext(ctx, `SELECT COALESCE(MAX(sibling_order) + 1, 0) FROM turns
		WHERE conversation_id = ? AND parent_turn_id IS ?`, turn.ConversationID, turn.ParentTurnID).Scan(&siblingOrder); err != nil {
		return Turn{}, err
	}
	turn.Sequence = nextSequence
	turn.SiblingOrder = siblingOrder
	if _, err := tx.ExecContext(ctx, `INSERT INTO turns(
		id, conversation_id, parent_turn_id, sequence, sibling_order, status, user_text,
		tool_events_json, metadata_json, created_at, updated_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, turn.ID, turn.ConversationID, turn.ParentTurnID,
		turn.Sequence, turn.SiblingOrder, turn.Status, turn.UserText, turn.ToolEventsJSON,
		turn.MetadataJSON, turn.CreatedAt, turn.UpdatedAt); err != nil {
		return Turn{}, err
	}
	if _, err := tx.ExecContext(ctx, `UPDATE conversations SET next_turn_sequence = ?, last_turn_at = ?, updated_at = ? WHERE id = ?`,
		nextSequence+1, turn.CreatedAt, turn.UpdatedAt, turn.ConversationID); err != nil {
		return Turn{}, err
	}
	if err := tx.Commit(); err != nil {
		return Turn{}, err
	}
	return turn, nil
}

func (r *SQLiteRepository) SetFinalTurn(ctx context.Context, conversationID, turnID, updatedAt string) (Turn, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return Turn{}, err
	}
	defer tx.Rollback()
	var status string
	if err := tx.QueryRowContext(ctx, `SELECT status FROM turns WHERE id=? AND conversation_id=?`, turnID, conversationID).Scan(&status); errors.Is(err, sql.ErrNoRows) {
		return Turn{}, errTurnNotFound
	} else if err != nil {
		return Turn{}, err
	}
	if status != TurnStatusCompleted {
		return Turn{}, errTurnStateInvalid
	}
	var hasChildren bool
	if err := tx.QueryRowContext(ctx, `SELECT EXISTS(SELECT 1 FROM turns WHERE parent_turn_id=?)`, turnID).Scan(&hasChildren); err != nil {
		return Turn{}, err
	}
	if hasChildren {
		return Turn{}, errTurnNotLeaf
	}
	result, err := tx.ExecContext(ctx, `UPDATE conversations SET final_turn_id=?,updated_at=? WHERE id=? AND status=?`, turnID, updatedAt, conversationID, ConversationStatusActive)
	if err != nil {
		return Turn{}, err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return Turn{}, errConversationNotFound
	}
	if err := tx.Commit(); err != nil {
		return Turn{}, err
	}
	return r.GetTurn(ctx, turnID)
}

func (r *SQLiteRepository) DeleteTurnSubtree(ctx context.Context, conversationID, turnID, updatedAt string) ([]string, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	var parent sql.NullString
	if err := tx.QueryRowContext(ctx, `SELECT parent_turn_id FROM turns WHERE id=? AND conversation_id=?`, turnID, conversationID).Scan(&parent); errors.Is(err, sql.ErrNoRows) {
		return nil, errTurnNotFound
	} else if err != nil {
		return nil, err
	}
	rows, err := tx.QueryContext(ctx, `WITH RECURSIVE subtree(id) AS (SELECT ? UNION ALL SELECT t.id FROM turns t JOIN subtree s ON t.parent_turn_id=s.id) SELECT id FROM subtree`, turnID)
	if err != nil {
		return nil, err
	}
	ids := []string{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			rows.Close()
			return nil, err
		}
		ids = append(ids, id)
	}
	rows.Close()
	var final sql.NullString
	if err := tx.QueryRowContext(ctx, `SELECT final_turn_id FROM conversations WHERE id=?`, conversationID).Scan(&final); err != nil {
		return nil, err
	}
	finalDeleted := false
	for _, id := range ids {
		if final.Valid && final.String == id {
			finalDeleted = true
		}
	}
	if _, err := tx.ExecContext(ctx, `DELETE FROM turns WHERE id IN (WITH RECURSIVE subtree(id) AS (SELECT ? UNION ALL SELECT t.id FROM turns t JOIN subtree s ON t.parent_turn_id=s.id) SELECT id FROM subtree)`, turnID); err != nil {
		return nil, err
	}
	if finalDeleted {
		var fallback any = nil
		if parent.Valid {
			var status string
			var children bool
			if err := tx.QueryRowContext(ctx, `SELECT status,EXISTS(SELECT 1 FROM turns WHERE parent_turn_id=?) FROM turns WHERE id=?`, parent.String, parent.String).Scan(&status, &children); err == nil && status == TurnStatusCompleted && !children {
				fallback = parent.String
			}
		}
		if _, err := tx.ExecContext(ctx, `UPDATE conversations SET final_turn_id=?,updated_at=? WHERE id=?`, fallback, updatedAt, conversationID); err != nil {
			return nil, err
		}
	} else if _, err := tx.ExecContext(ctx, `UPDATE conversations SET updated_at=? WHERE id=?`, updatedAt, conversationID); err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return ids, nil
}

func (r *SQLiteRepository) GetTurn(ctx context.Context, id string) (Turn, error) {
	turn, err := scanTurn(r.db.QueryRowContext(ctx, turnSelect+` WHERE t.id = ?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		return Turn{}, errTurnNotFound
	}
	return turn, err
}

func (r *SQLiteRepository) ListTurns(ctx context.Context, conversationID string) ([]Turn, error) {
	if _, err := r.GetConversation(ctx, conversationID, false); err != nil {
		return nil, err
	}
	rows, err := r.db.QueryContext(ctx, turnSelect+` WHERE t.conversation_id = ? ORDER BY t.sequence`, conversationID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := make([]Turn, 0)
	for rows.Next() {
		turn, err := scanTurn(rows)
		if err != nil {
			return nil, err
		}
		result = append(result, turn)
	}
	return result, rows.Err()
}

func (r *SQLiteRepository) ListTurnPage(ctx context.Context, conversationID string, limit, beforeSequence int) ([]Turn, error) {
	if _, err := r.GetConversation(ctx, conversationID, false); err != nil {
		return nil, err
	}
	query := turnSelect + ` WHERE t.conversation_id = ?`
	arguments := []any{conversationID}
	if beforeSequence > 0 {
		query += ` AND t.sequence < ?`
		arguments = append(arguments, beforeSequence)
	}
	query += ` ORDER BY t.sequence DESC, t.id DESC LIMIT ?`
	arguments = append(arguments, limit)
	rows, err := r.db.QueryContext(ctx, query, arguments...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	result := make([]Turn, 0, limit)
	for rows.Next() {
		turn, err := scanTurn(rows)
		if err != nil {
			return nil, err
		}
		result = append(result, turn)
	}
	return result, rows.Err()
}

func (r *SQLiteRepository) RecoverInterruptedTurns(ctx context.Context, workspaceID, updatedAt, errorMessage string) (int, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return 0, err
	}
	defer tx.Rollback()
	if _, err := tx.ExecContext(ctx, `UPDATE conversations SET updated_at = ?
		WHERE workspace_id = ? AND status = ? AND EXISTS (
			SELECT 1 FROM turns WHERE turns.conversation_id = conversations.id AND turns.status IN (?, ?)
		)`, updatedAt, workspaceID, ConversationStatusActive, TurnStatusQueued, TurnStatusRunning); err != nil {
		return 0, err
	}
	result, err := tx.ExecContext(ctx, `UPDATE turns SET status = ?, error_message = ?, updated_at = ?
		WHERE status IN (?, ?) AND conversation_id IN (
			SELECT id FROM conversations WHERE workspace_id = ? AND status = ?
		)`, TurnStatusFailed, errorMessage, updatedAt, TurnStatusQueued, TurnStatusRunning,
		workspaceID, ConversationStatusActive)
	if err != nil {
		return 0, err
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return 0, err
	}
	if err := tx.Commit(); err != nil {
		return 0, err
	}
	return int(affected), nil
}

func (r *SQLiteRepository) CompleteTurn(ctx context.Context, turn Turn) (Turn, error) {
	result, err := r.db.ExecContext(ctx, `UPDATE turns SET status = ?, result_kind = ?, assistant_text = ?,
		tool_events_json = ?, metadata_json = CASE WHEN ? = '' THEN metadata_json ELSE ? END,
		code_snapshot = ?, result_json = ?, error_message = '', updated_at = ?
		WHERE id = ? AND status IN (?, ?)`, TurnStatusCompleted, turn.ResultKind, turn.AssistantText,
		turn.ToolEventsJSON, turn.MetadataJSON, turn.MetadataJSON, turn.CodeSnapshot, turn.ResultJSON,
		turn.UpdatedAt, turn.ID, TurnStatusQueued, TurnStatusRunning)
	if err != nil {
		return Turn{}, err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		if _, lookupErr := r.GetTurn(ctx, turn.ID); errors.Is(lookupErr, errTurnNotFound) {
			return Turn{}, errTurnNotFound
		}
		return Turn{}, errTurnStateInvalid
	}
	return r.GetTurn(ctx, turn.ID)
}

func (r *SQLiteRepository) FailTurn(ctx context.Context, turn Turn) (Turn, error) {
	result, err := r.db.ExecContext(ctx, `UPDATE turns SET status = ?, assistant_text = ?, tool_events_json = ?,
		metadata_json = CASE WHEN ? = '' THEN metadata_json ELSE ? END,
		code_snapshot = ?, error_message = ?, updated_at = ? WHERE id = ? AND status IN (?, ?)`,
		TurnStatusFailed, turn.AssistantText, turn.ToolEventsJSON, turn.MetadataJSON, turn.MetadataJSON, turn.CodeSnapshot, turn.ErrorMessage,
		turn.UpdatedAt, turn.ID, TurnStatusQueued, TurnStatusRunning)
	if err != nil {
		return Turn{}, err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		if _, lookupErr := r.GetTurn(ctx, turn.ID); errors.Is(lookupErr, errTurnNotFound) {
			return Turn{}, errTurnNotFound
		}
		return Turn{}, errTurnStateInvalid
	}
	return r.GetTurn(ctx, turn.ID)
}

func (r *SQLiteRepository) CreateArtifact(ctx context.Context, artifact Artifact) error {
	_, err := r.db.ExecContext(ctx, `INSERT INTO artifacts(
		id, workspace_id, conversation_id, turn_id, kind, logical_name, display_name,
		storage_class, relative_path, payload_format, media_type, byte_size, sha256, status, created_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, artifact.ID, artifact.WorkspaceID,
		artifact.ConversationID, artifact.TurnID, artifact.Kind, artifact.LogicalName, artifact.DisplayName,
		artifact.StorageClass, artifact.RelativePath, artifact.PayloadFormat, artifact.MediaType,
		artifact.ByteSize, artifact.SHA256, artifact.Status, artifact.CreatedAt)
	return err
}

func (r *SQLiteRepository) GetArtifact(ctx context.Context, id string) (Artifact, error) {
	artifact, err := scanArtifact(r.db.QueryRowContext(ctx, artifactSelect+` WHERE a.id = ?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		return Artifact{}, errArtifactNotFound
	}
	return artifact, err
}

func (r *SQLiteRepository) ListArtifacts(ctx context.Context, turnID string) ([]Artifact, error) {
	if _, err := r.GetTurn(ctx, turnID); err != nil {
		return nil, err
	}
	rows, err := r.db.QueryContext(ctx, artifactSelect+` WHERE a.turn_id = ? ORDER BY a.created_at, a.id`, turnID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArtifacts(rows)
}

func (r *SQLiteRepository) ListConversationArtifacts(ctx context.Context, conversationID string) ([]Artifact, error) {
	rows, err := r.db.QueryContext(ctx, artifactSelect+` WHERE a.conversation_id = ? ORDER BY a.created_at, a.id`, conversationID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanArtifacts(rows)
}

func (r *SQLiteRepository) SetArtifactStatus(ctx context.Context, id, status string) error {
	result, err := r.db.ExecContext(ctx, `UPDATE artifacts SET status = ? WHERE id = ?`, status, id)
	if err != nil {
		return err
	}
	if affected, _ := result.RowsAffected(); affected == 0 {
		return errArtifactNotFound
	}
	return nil
}

func (r *SQLiteRepository) DeleteArtifact(ctx context.Context, id string) error {
	result, err := r.db.ExecContext(ctx, `DELETE FROM artifacts WHERE id=?`, id)
	if err != nil {
		return err
	}
	if n, _ := result.RowsAffected(); n == 0 {
		return errArtifactNotFound
	}
	return nil
}

func (r *SQLiteRepository) Close() error { return r.db.Close() }

const turnSelect = `SELECT t.id, t.conversation_id, t.parent_turn_id, t.sequence, t.sibling_order,
	t.status, t.result_kind, t.user_text, t.assistant_text, t.tool_events_json, t.metadata_json,
	t.code_snapshot, t.result_json, t.error_message, t.created_at, t.updated_at FROM turns t`

const artifactSelect = `SELECT a.id, a.workspace_id, a.conversation_id, a.turn_id, a.kind,
	a.logical_name, a.display_name, a.storage_class, a.relative_path, a.payload_format, a.media_type,
	a.byte_size, a.sha256, a.status, a.created_at FROM artifacts a`

type scanner interface {
	Scan(...any) error
}

func scanConversation(row scanner) (Conversation, error) {
	var conversation Conversation
	var final sql.NullString
	err := row.Scan(&conversation.ID, &conversation.WorkspaceID, &conversation.Title, &conversation.Status,
		&final, &conversation.LastTurnAt, &conversation.CreatedAt, &conversation.UpdatedAt)
	if final.Valid {
		conversation.FinalTurnID = &final.String
	}
	return conversation, err
}

func scanTurn(row scanner) (Turn, error) {
	var turn Turn
	var parent sql.NullString
	err := row.Scan(&turn.ID, &turn.ConversationID, &parent, &turn.Sequence, &turn.SiblingOrder,
		&turn.Status, &turn.ResultKind, &turn.UserText, &turn.AssistantText, &turn.ToolEventsJSON,
		&turn.MetadataJSON, &turn.CodeSnapshot, &turn.ResultJSON, &turn.ErrorMessage, &turn.CreatedAt, &turn.UpdatedAt)
	if parent.Valid {
		turn.ParentTurnID = &parent.String
	}
	return turn, err
}

func scanArtifact(row scanner) (Artifact, error) {
	var artifact Artifact
	err := row.Scan(&artifact.ID, &artifact.WorkspaceID, &artifact.ConversationID, &artifact.TurnID,
		&artifact.Kind, &artifact.LogicalName, &artifact.DisplayName, &artifact.StorageClass,
		&artifact.RelativePath, &artifact.PayloadFormat, &artifact.MediaType, &artifact.ByteSize,
		&artifact.SHA256, &artifact.Status, &artifact.CreatedAt)
	return artifact, err
}

func scanArtifacts(rows *sql.Rows) ([]Artifact, error) {
	result := make([]Artifact, 0)
	for rows.Next() {
		artifact, err := scanArtifact(rows)
		if err != nil {
			return nil, err
		}
		result = append(result, artifact)
	}
	return result, rows.Err()
}
