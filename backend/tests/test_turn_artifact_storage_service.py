from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.turn_artifact_storage_service import TurnArtifactStorageService


@pytest.mark.asyncio
async def test_persist_turn_artifacts_uses_kernel_materialization_without_direct_scratchpad_reads(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-1"
    (workspace_dir / "scratchpad").mkdir(parents=True, exist_ok=True)
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
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.ArtifactScratchpadStore.get_artifact",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("scratchpad lookup should not run during live export")),
    )

    async def fake_materialize_workspace_artifacts_via_kernel(workspace_id, specs):
        assert workspace_id == "workspace-1"
        for spec in specs:
            target = Path(spec["storage_path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            if spec["kind"] == "dataframe":
                target.write_bytes(b"PAR1")
            else:
                target.write_text(json.dumps(spec["payload"]), encoding="utf-8")
        return [
            {"artifact_id": "df-1", "size_bytes": 4},
            {"artifact_id": "fig-1", "size_bytes": 37},
        ]

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.materialize_workspace_artifacts_via_kernel",
        fake_materialize_workspace_artifacts_via_kernel,
    )

    rows = await TurnArtifactStorageService.persist_turn_artifacts(
        session=SimpleNamespace(),
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        workspace_duckdb_path=str(workspace_dir / "workspace.db"),
        artifacts=[
            {
                "artifact_id": "df-1",
                "kind": "dataframe",
                "logical_name": "summary_df",
                "table_name": "art_turn_1",
                "row_count": 1,
                "schema": [{"name": "amount", "dtype": "INTEGER"}],
            },
            {
                "artifact_id": "fig-1",
                "kind": "figure",
                "logical_name": "sales_chart",
                "payload": {"figure": {"data": [], "layout": {}}},
            },
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
    assert rows[0]["size_bytes"] == 4
    assert captured["workspace_id"] == "workspace-1"
    assert captured["conversation_id"] == "conversation-1"
    assert captured["turn_id"] == "turn-1"
    assert len(captured["items"]) == 2
