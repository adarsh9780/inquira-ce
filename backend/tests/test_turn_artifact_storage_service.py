from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from app.v1.services.turn_artifact_storage_service import TurnArtifactStorageService


@pytest.mark.asyncio
async def test_persist_turn_artifacts_writes_turn_owned_files_and_metadata(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-1"
    scratchpad_dir = workspace_dir / "scratchpad"
    scratchpad_dir.mkdir(parents=True, exist_ok=True)
    scratchpad_db = scratchpad_dir / "artifacts.duckdb"

    con = duckdb.connect(str(scratchpad_db))
    try:
        con.execute(
            """
            CREATE TABLE artifact_manifest (
                artifact_id TEXT,
                run_id TEXT,
                workspace_id TEXT,
                logical_name TEXT,
                kind TEXT,
                table_name TEXT,
                payload_json TEXT,
                schema_json TEXT,
                row_count BIGINT,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                status TEXT,
                error TEXT
            )
            """
        )
        con.execute("CREATE TABLE art_turn_1 AS SELECT 1 AS amount, 'north' AS region")
        con.execute(
            """
            INSERT INTO artifact_manifest
            VALUES
            ('df-1', 'run-1', 'workspace-1', 'summary_df', 'dataframe', 'art_turn_1', '{"title":"Revenue"}',
             '[{"name":"amount","dtype":"INTEGER"},{"name":"region","dtype":"VARCHAR"}]', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'ready', NULL),
            ('fig-1', 'run-1', 'workspace-1', 'sales_chart', 'figure', NULL, '{"figure":{"data":[],"layout":{}}}', NULL, NULL,
             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'ready', NULL)
            """
        )
    finally:
        con.close()

    captured: dict[str, object] = {}

    async def fake_replace_for_turn(session, *, workspace_id, conversation_id, turn_id, items):
        _ = session
        captured["workspace_id"] = workspace_id
        captured["conversation_id"] = conversation_id
        captured["turn_id"] = turn_id
        captured["items"] = items
        return []

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.TurnArtifactRepository.replace_for_turn",
        fake_replace_for_turn,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_storage_service.WorkspaceStorageService.build_workspace_dir",
        lambda username, workspace_id: tmp_path / username / workspace_id,
    )

    rows = await TurnArtifactStorageService.persist_turn_artifacts(
        session=SimpleNamespace(),
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        workspace_duckdb_path=str(workspace_dir / "workspace.db"),
        artifacts=[
            {"artifact_id": "df-1", "kind": "dataframe", "logical_name": "summary_df"},
            {"artifact_id": "fig-1", "kind": "figure", "logical_name": "sales_chart"},
        ],
    )

    artifacts_dir = tmp_path / "alice" / "workspace-1" / "conversations" / "conversation-1" / "turns" / "turn-1" / "artifacts"
    dataframe_path = artifacts_dir / "df-1.parquet"
    figure_path = artifacts_dir / "fig-1.json"

    assert dataframe_path.is_file()
    assert figure_path.is_file()
    assert rows[0]["payload_format"] == "parquet"
    assert rows[1]["payload_format"] == "json"
    assert rows[0]["storage_path"] == str(dataframe_path)
    assert json.loads(figure_path.read_text(encoding="utf-8"))["figure"] == {"data": [], "layout": {}}
    assert captured["workspace_id"] == "workspace-1"
    assert captured["conversation_id"] == "conversation-1"
    assert captured["turn_id"] == "turn-1"
    assert len(captured["items"]) == 2
