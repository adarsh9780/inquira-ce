# DB Split Migration v3 Runbook (One-Shot Cutover)

This runbook performs a one-time split from `app_v1.db` into:
- `auth_v1.db` (auth/session)
- `appdata_v1.db` (workspace/chat/product data)

No temporary migration logic is required in runtime service code.

## 1) Pre-cutover checks

1. Put backend in maintenance mode (block writes).
2. Verify source DB exists:
   - `~/.inquira/app_v1.db`
3. Backup source DB:
   - `cp ~/.inquira/app_v1.db ~/.inquira/app_v1.db.backup.$(date +%Y%m%d_%H%M%S)`

## 2) Create/clean target DB files

```bash
rm -f ~/.inquira/auth_v1.db ~/.inquira/appdata_v1.db
touch ~/.inquira/auth_v1.db ~/.inquira/appdata_v1.db
```

## 3) Apply schema migrations (no data copy yet)

Run from `backend/`:

```bash
uv run alembic -x db=auth upgrade head
uv run alembic -x db=appdata upgrade head
```

If you use env vars during release:
- `INQUIRA_AUTH_DB_URL=sqlite+aiosqlite:///$HOME/.inquira/auth_v1.db`
- `INQUIRA_APPDATA_DB_URL=sqlite+aiosqlite:///$HOME/.inquira/appdata_v1.db`

## 4) One-shot data copy using sqlite3 utility

```bash
sqlite3 ~/.inquira/app_v1.db <<'SQL'
PRAGMA foreign_keys=OFF;

ATTACH DATABASE '/Users/<your-user>/.inquira/auth_v1.db' AS authdb;
ATTACH DATABASE '/Users/<your-user>/.inquira/appdata_v1.db' AS appdb;

BEGIN;

DELETE FROM authdb.v1_user_sessions;
DELETE FROM authdb.v1_users;
DELETE FROM appdb.v1_user_preferences;
DELETE FROM appdb.v1_workspace_deletion_jobs;
DELETE FROM appdb.v1_turns;
DELETE FROM appdb.v1_conversations;
DELETE FROM appdb.v1_workspace_datasets;
DELETE FROM appdb.v1_workspaces;
DELETE FROM appdb.v1_principals;

INSERT INTO authdb.v1_users (id, username, password_hash, salt, plan, created_at, updated_at)
SELECT id, username, password_hash, salt, plan, created_at, updated_at
FROM main.v1_users;

INSERT INTO authdb.v1_user_sessions (session_token, user_id, created_at)
SELECT session_token, user_id, created_at
FROM main.v1_user_sessions;

INSERT INTO appdb.v1_principals (id, username_cached, plan_cached, created_at, updated_at)
SELECT id, username, plan, created_at, updated_at
FROM main.v1_users;

INSERT INTO appdb.v1_workspaces (id, owner_principal_id, name, name_normalized, is_active, duckdb_path, created_at, updated_at)
SELECT id, user_id, name, name_normalized, is_active, duckdb_path, created_at, updated_at
FROM main.v1_workspaces;

INSERT INTO appdb.v1_workspace_datasets (
    id, workspace_id, source_path, source_fingerprint, table_name, schema_path,
    file_size, source_mtime, row_count, file_type, created_at, updated_at
)
SELECT
    id, workspace_id, source_path, source_fingerprint, table_name, schema_path,
    file_size, source_mtime, row_count, file_type, created_at, updated_at
FROM main.v1_workspace_datasets;

INSERT INTO appdb.v1_conversations (
    id, workspace_id, title, created_by_principal_id, last_turn_at, created_at, updated_at
)
SELECT
    id, workspace_id, title, created_by_user_id, last_turn_at, created_at, updated_at
FROM main.v1_conversations;

INSERT INTO appdb.v1_turns (
    id, conversation_id, seq_no, user_text, assistant_text, tool_events_json, metadata_json, code_snapshot, created_at
)
SELECT
    id, conversation_id, seq_no, user_text, assistant_text, tool_events_json, metadata_json, code_snapshot, created_at
FROM main.v1_turns;

INSERT INTO appdb.v1_workspace_deletion_jobs (
    id, owner_principal_id, workspace_id, status, error_message, created_at, updated_at
)
SELECT
    id, user_id, workspace_id, status, error_message, created_at, updated_at
FROM main.v1_workspace_deletion_jobs;

INSERT INTO appdb.v1_user_preferences (
    principal_id, selected_model, schema_context, allow_schema_sample_values,
    chat_overlay_width, is_sidebar_collapsed, hide_shortcuts_modal,
    active_workspace_id, active_dataset_path, active_table_name, created_at, updated_at
)
SELECT
    user_id, selected_model, schema_context, allow_schema_sample_values,
    chat_overlay_width, is_sidebar_collapsed, hide_shortcuts_modal,
    active_workspace_id, active_dataset_path, active_table_name, created_at, updated_at
FROM main.v1_user_preferences;

COMMIT;

PRAGMA foreign_keys=ON;
DETACH DATABASE authdb;
DETACH DATABASE appdb;
SQL
```

## 5) Verification SQL checklist

```bash
sqlite3 ~/.inquira/app_v1.db "SELECT 'v1_users', COUNT(*) FROM v1_users;"
sqlite3 ~/.inquira/auth_v1.db "SELECT 'v1_users', COUNT(*) FROM v1_users; SELECT 'v1_user_sessions', COUNT(*) FROM v1_user_sessions;"
sqlite3 ~/.inquira/appdata_v1.db "SELECT 'v1_principals', COUNT(*) FROM v1_principals; SELECT 'v1_workspaces', COUNT(*) FROM v1_workspaces; SELECT 'v1_conversations', COUNT(*) FROM v1_conversations; SELECT 'v1_turns', COUNT(*) FROM v1_turns; SELECT 'v1_workspace_datasets', COUNT(*) FROM v1_workspace_datasets; SELECT 'v1_workspace_deletion_jobs', COUNT(*) FROM v1_workspace_deletion_jobs; SELECT 'v1_user_preferences', COUNT(*) FROM v1_user_preferences;"
sqlite3 ~/.inquira/auth_v1.db "PRAGMA foreign_key_check;"
sqlite3 ~/.inquira/appdata_v1.db "PRAGMA foreign_key_check;"
```

`PRAGMA foreign_key_check;` must return no rows.

## 6) App config cutover

Start backend with split config only:

```bash
export INQUIRA_AUTH_DB_URL="sqlite+aiosqlite:///$HOME/.inquira/auth_v1.db"
export INQUIRA_APPDATA_DB_URL="sqlite+aiosqlite:///$HOME/.inquira/appdata_v1.db"
```

Then run smoke suite:
1. Register/login/me/logout.
2. Workspace list/create/activate/delete.
3. Conversation create/list/rename/clear/delete.
4. Chat analyze + streaming path.
5. Verify persisted assistant text for code answers is still populated.

## 7) Rollback

If validation fails before reopen:
1. Stop cutover.
2. Restore backend env/config to old single-DB release.
3. Restore source DB backup file.
4. Reopen traffic.
