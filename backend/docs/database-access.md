# Database Access Rules

This backend uses four storage resources. Each one has one owner and one approved access path.

## Registry

- `auth_sqlite`
  - Role: `control_plane`
  - Owner: request-scoped SQLAlchemy session
  - Access path: repositories on top of `backend/app/v1/db/session.py`

- `appdata_sqlite`
  - Role: `control_plane`
  - Owner: request-scoped SQLAlchemy session
  - Access path: repositories on top of `backend/app/v1/db/session.py`

- `workspace_duckdb`
  - Role: `workspace_data`
  - Owner: workspace kernel while runtime is active
  - Live access path: `backend/app/data_access/workspace_db.py` runtime adapter
  - Offline access path: `backend/app/data_access/workspace_db.py` offline adapter with a maintenance lease

- `turn_blob_store`
  - Role: `artifact_blob`
  - Owner: filesystem-backed turn/conversation storage
  - Access path: turn bundle and turn artifact services

## Runtime vs Offline Access

- Use a runtime adapter when the workspace kernel owns the DuckDB file.
- Use an offline adapter only after the workspace runtime is drained and a maintenance lease is held.
- Do not open workspace DuckDB files directly from feature code.

## Adding a New Database

1. Add a `DatabaseSpec` to `backend/app/data_access/registry.py`.
2. Decide the owner: request session, kernel-owned runtime, or offline maintenance.
3. Add one adapter module for live and/or offline access.
4. Add lease or job-claim coordination if the resource can conflict with background work.
5. Extend the guardrail tests so raw connections cannot bypass the adapter layer.
