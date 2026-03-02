"""Workspace scratchpad artifact persistence and retrieval utilities."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb


_DEFAULT_TTL_HOURS = 48


@dataclass(frozen=True)
class ScratchpadConfig:
    ttl_hours: int = _DEFAULT_TTL_HOURS
    max_bytes: int = 10 * 1024 * 1024 * 1024


class ArtifactScratchpadStore:
    """Manifest-backed artifact store per workspace scratchpad."""

    def __init__(self, config: ScratchpadConfig | None = None) -> None:
        self._config = config or ScratchpadConfig()

    @staticmethod
    def build_scratchpad_dir(workspace_duckdb_path: str) -> Path:
        return Path(workspace_duckdb_path).parent / "scratchpad"

    @staticmethod
    def build_scratchpad_db_path(workspace_duckdb_path: str) -> Path:
        return ArtifactScratchpadStore.build_scratchpad_dir(workspace_duckdb_path) / "artifacts.duckdb"

    @staticmethod
    def _quoted(ident: str) -> str:
        return '"' + str(ident).replace('"', '""') + '"'

    @staticmethod
    def _safe_table_name(run_id: str, seq: int) -> str:
        run_short = re.sub(r"[^A-Za-z0-9]", "", str(run_id))[:12] or "run"
        return f"art_{run_short}_{max(1, int(seq))}"

    def ensure_workspace(self, workspace_duckdb_path: str) -> Path:
        db_path = self.build_scratchpad_db_path(workspace_duckdb_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(db_path), read_only=False)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS artifact_manifest (
                    artifact_id VARCHAR PRIMARY KEY,
                    run_id VARCHAR NOT NULL,
                    workspace_id VARCHAR NOT NULL,
                    logical_name VARCHAR NOT NULL,
                    kind VARCHAR NOT NULL,
                    table_name VARCHAR,
                    payload_json TEXT,
                    schema_json TEXT,
                    row_count BIGINT,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    status VARCHAR NOT NULL,
                    error TEXT
                )
                """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_manifest_run_id
                ON artifact_manifest(run_id)
                """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_manifest_workspace_id
                ON artifact_manifest(workspace_id)
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS run_manifest (
                    run_id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    conversation_id VARCHAR,
                    turn_id VARCHAR,
                    question TEXT,
                    generated_code TEXT,
                    executed_code TEXT,
                    stdout TEXT,
                    stderr TEXT,
                    execution_status VARCHAR NOT NULL,
                    retry_count INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
                """
            )
        finally:
            con.close()
        return db_path

    def write_run_manifest(
        self,
        *,
        workspace_duckdb_path: str,
        run_id: str,
        workspace_id: str,
        conversation_id: str | None,
        turn_id: str | None,
        question: str,
        generated_code: str,
        executed_code: str,
        stdout: str,
        stderr: str,
        execution_status: str,
        retry_count: int,
    ) -> None:
        db_path = self.ensure_workspace(workspace_duckdb_path)
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=max(1, self._config.ttl_hours))
        con = duckdb.connect(str(db_path), read_only=False)
        try:
            con.execute(
                """
                INSERT OR REPLACE INTO run_manifest (
                    run_id, workspace_id, conversation_id, turn_id, question,
                    generated_code, executed_code, stdout, stderr,
                    execution_status, retry_count, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    workspace_id,
                    conversation_id,
                    turn_id,
                    question,
                    generated_code,
                    executed_code,
                    stdout,
                    stderr,
                    execution_status,
                    int(retry_count),
                    now,
                    expires_at,
                ],
            )
        finally:
            con.close()

    def store_script_artifact(
        self,
        *,
        workspace_duckdb_path: str,
        workspace_id: str,
        run_id: str,
        script_text: str,
        logical_name: str = "final_script",
    ) -> str:
        db_path = self.ensure_workspace(workspace_duckdb_path)
        artifact_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=max(1, self._config.ttl_hours))
        payload = json.dumps({"script": script_text}, ensure_ascii=True)
        con = duckdb.connect(str(db_path), read_only=False)
        try:
            con.execute(
                """
                INSERT INTO artifact_manifest (
                    artifact_id, run_id, workspace_id, logical_name, kind,
                    table_name, payload_json, schema_json, row_count,
                    created_at, expires_at, status, error
                ) VALUES (?, ?, ?, ?, 'script', NULL, ?, NULL, NULL, ?, ?, 'ready', NULL)
                """,
                [artifact_id, run_id, workspace_id, logical_name, payload, now, expires_at],
            )
        finally:
            con.close()
        return artifact_id

    def get_artifact(self, *, workspace_duckdb_path: str, artifact_id: str) -> dict[str, Any] | None:
        db_path = self.ensure_workspace(workspace_duckdb_path)
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            row = con.execute(
                """
                SELECT artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                       payload_json, schema_json, row_count, created_at, expires_at, status, error
                FROM artifact_manifest
                WHERE artifact_id = ?
                LIMIT 1
                """,
                [artifact_id],
            ).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        schema = None
        payload = None
        try:
            if row[7]:
                schema = json.loads(str(row[7]))
        except Exception:
            schema = None
        try:
            if row[6]:
                payload = json.loads(str(row[6]))
        except Exception:
            payload = None
        return {
            "artifact_id": str(row[0]),
            "run_id": str(row[1]),
            "workspace_id": str(row[2]),
            "logical_name": str(row[3]),
            "kind": str(row[4]),
            "table_name": str(row[5]) if row[5] is not None else None,
            "payload": payload,
            "schema": schema,
            "row_count": int(row[8] or 0) if row[8] is not None else None,
            "created_at": str(row[9]),
            "expires_at": str(row[10]),
            "status": str(row[11]),
            "error": str(row[12]) if row[12] is not None else None,
            "pointer": f"duckdb://scratchpad/artifacts.duckdb#artifact={row[0]}",
        }

    def list_artifacts_for_run(self, *, workspace_duckdb_path: str, run_id: str) -> list[dict[str, Any]]:
        db_path = self.ensure_workspace(workspace_duckdb_path)
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            rows = con.execute(
                """
                SELECT artifact_id
                FROM artifact_manifest
                WHERE run_id = ?
                ORDER BY created_at ASC
                """,
                [run_id],
            ).fetchall()
        finally:
            con.close()
        artifacts: list[dict[str, Any]] = []
        for row in rows:
            item = self.get_artifact(workspace_duckdb_path=workspace_duckdb_path, artifact_id=str(row[0]))
            if item is None:
                continue
            artifacts.append(item)
        return artifacts

    def get_dataframe_rows(
        self,
        *,
        workspace_duckdb_path: str,
        artifact_id: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any] | None:
        meta = self.get_artifact(workspace_duckdb_path=workspace_duckdb_path, artifact_id=artifact_id)
        if meta is None or meta.get("kind") != "dataframe":
            return None
        table_name = str(meta.get("table_name") or "").strip()
        if not table_name:
            return None
        db_path = self.ensure_workspace(workspace_duckdb_path)
        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(1000, int(limit)))
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            escaped = table_name.replace('"', '""')
            page_df = con.execute(
                f'SELECT * FROM "{escaped}" LIMIT {safe_limit} OFFSET {safe_offset}'
            ).fetchdf()
            rows = json.loads(page_df.to_json(orient="records", date_format="iso"))
            columns = [str(c) for c in list(page_df.columns)]
            row_count = con.execute(
                f'SELECT COUNT(*) FROM "{escaped}"'
            ).fetchone()
        finally:
            con.close()
        return {
            "artifact_id": artifact_id,
            "name": meta.get("logical_name") or "dataframe",
            "row_count": int((row_count or [0])[0] or 0),
            "columns": columns,
            "rows": rows,
            "offset": safe_offset,
            "limit": safe_limit,
        }

    def prune_workspace(self, *, workspace_duckdb_path: str) -> None:
        db_path = self.build_scratchpad_db_path(workspace_duckdb_path)
        if not db_path.exists():
            return
        con = duckdb.connect(str(db_path), read_only=False)
        now = datetime.now(UTC)
        try:
            expired_tables = con.execute(
                """
                SELECT table_name
                FROM artifact_manifest
                WHERE kind = 'dataframe' AND table_name IS NOT NULL AND expires_at < ?
                """,
                [now],
            ).fetchall()
            for (table_name,) in expired_tables:
                if not table_name:
                    continue
                escaped = str(table_name).replace('"', '""')
                con.execute(f'DROP TABLE IF EXISTS "{escaped}"')
            con.execute("DELETE FROM artifact_manifest WHERE expires_at < ?", [now])
            con.execute("DELETE FROM run_manifest WHERE expires_at < ?", [now])
        finally:
            con.close()

    def prune_all(self, *, inquira_root: Path | None = None) -> None:
        root = inquira_root or (Path.home() / ".inquira")
        if not root.exists():
            return
        for artifacts_db in root.glob("*/workspaces/*/scratchpad/artifacts.duckdb"):
            workspace_duckdb_path = str(artifacts_db.parent.parent / "workspace.duckdb")
            self.prune_workspace(workspace_duckdb_path=workspace_duckdb_path)


_scratchpad_store = ArtifactScratchpadStore()


def get_artifact_scratchpad_store() -> ArtifactScratchpadStore:
    return _scratchpad_store
