from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.v1.services.turn_artifact_storage_service import TurnArtifactStorageService


def test_artifact_identity_keeps_logical_name_in_artifact_id_and_dedupes() -> None:
    normalized = TurnArtifactStorageService._normalize_artifact_identities(
        [
            {"artifact_id": "df-1", "kind": "dataframe", "logical_name": "Sales Summary"},
            {"artifact_id": "df-1", "kind": "dataframe", "logical_name": "Sales Summary"},
            {"artifact_id": "sales_summary__df-3", "kind": "dataframe", "logical_name": "sales_summary"},
        ],
        turn_id="turn-1",
    )

    assert normalized[0]["artifact_id"] == "Sales_Summary__df-1"
    assert normalized[0]["source_artifact_id"] == "df-1"
    assert normalized[0]["display_name"] == "Sales Summary"
    assert normalized[1]["artifact_id"] == "Sales_Summary__df-1__2"
    assert normalized[2]["artifact_id"] == "sales_summary_df-3"


@pytest.mark.asyncio
async def test_persist_turn_artifacts_uses_existing_turn_files(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-1"
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
    artifacts_dir = tmp_path / "alice" / "workspace-1" / "conversations" / "conversation-1" / "turn-1"
    dataframe_path = artifacts_dir / "summary_df__df-1.parquet"
    figure_path = artifacts_dir / "sales_chart__fig-1.json"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    dataframe_path.write_bytes(b"PAR1")
    figure_path.write_text(json.dumps({"figure": {"data": [], "layout": {}}}), encoding="utf-8")

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
                "storage_path": str(dataframe_path),
                "row_count": 1,
                "schema": [{"name": "amount", "dtype": "INTEGER"}],
            },
            {
                "artifact_id": "fig-1",
                "kind": "figure",
                "logical_name": "sales_chart",
                "storage_path": str(figure_path),
                "payload": {"figure": {"data": [], "layout": {}}},
            },
        ],
    )

    assert dataframe_path.is_file()
    assert figure_path.is_file()
    assert rows[0]["artifact_id"] == "summary_df__df-1"
    assert rows[0]["source_artifact_id"] == "df-1"
    assert rows[0]["logical_name"] == "summary_df"
    assert rows[0]["display_name"] == "Summary Df"
    assert rows[0]["payload_format"] == "parquet"
    assert rows[1]["payload_format"] == "json"
    assert rows[0]["storage_path"] == str(dataframe_path)
    assert json.loads(figure_path.read_text(encoding="utf-8"))["figure"] == {"data": [], "layout": {}}
    assert rows[0]["size_bytes"] == 4
    assert captured["workspace_id"] == "workspace-1"
    assert captured["conversation_id"] == "conversation-1"
    assert captured["turn_id"] == "turn-1"
    assert len(captured["items"]) == 2


@pytest.mark.asyncio
async def test_persist_turn_artifacts_fails_when_json_export_file_missing(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-2"
    captured: dict[str, object] = {}

    async def fake_replace_for_turn(session, *, workspace_id, conversation_id, turn_id, items):
        _ = session
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
    missing_path = (
        tmp_path
        / "alice"
        / "workspace-2"
        / "conversations"
        / "conversation-2"
        / "turn-2"
        / "missing-chart.json"
    )
    with pytest.raises(FileNotFoundError, match="Turn artifact file is missing"):
        await TurnArtifactStorageService.persist_turn_artifacts(
            session=SimpleNamespace(),
            username="alice",
            workspace_id="workspace-2",
            conversation_id="conversation-2",
            turn_id="turn-2",
            workspace_duckdb_path=str(workspace_dir / "workspace.db"),
            artifacts=[
                {
                    "artifact_id": "fig-2",
                    "kind": "figure",
                    "logical_name": "trend_chart",
                    "storage_path": str(missing_path),
                    "payload": {"figure": {"data": [1], "layout": {}}},
                    "created_at": "2026-05-18T04:00:00+00:00",
                },
            ],
        )

    assert "items" not in captured


@pytest.mark.asyncio
async def test_persist_turn_artifacts_fails_when_dataframe_export_file_missing(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-3"
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
    missing_path = (
        tmp_path
        / "alice"
        / "workspace-3"
        / "conversations"
        / "conversation-3"
        / "turn-3"
        / "missing-df.parquet"
    )
    with pytest.raises(FileNotFoundError, match="Turn artifact file is missing"):
        await TurnArtifactStorageService.persist_turn_artifacts(
            session=SimpleNamespace(),
            username="alice",
            workspace_id="workspace-3",
            conversation_id="conversation-3",
            turn_id="turn-3",
            workspace_duckdb_path=str(workspace_dir / "workspace.db"),
            artifacts=[
                {
                    "artifact_id": "df-3",
                    "kind": "dataframe",
                    "logical_name": "summary_df",
                    "storage_path": str(missing_path),
                },
            ],
        )

    assert "items" not in captured


@pytest.mark.asyncio
async def test_persist_turn_artifacts_rejects_file_outside_owned_turn(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "app.v1.services.workspace_storage_service.WorkspaceStorageService.build_workspace_dir",
        lambda username, workspace_id: tmp_path / username / workspace_id,
    )
    external_path = tmp_path / "external-secret.json"
    external_path.write_text('{"secret": true}', encoding="utf-8")

    with pytest.raises(ValueError, match="must remain inside"):
        await TurnArtifactStorageService.persist_turn_artifacts(
            session=SimpleNamespace(),
            username="alice",
            workspace_id="workspace-4",
            conversation_id="conversation-4",
            turn_id="turn-4",
            workspace_duckdb_path=str(tmp_path / "alice" / "workspace-4" / "workspace.db"),
            artifacts=[
                {
                    "artifact_id": "external",
                    "kind": "structured",
                    "logical_name": "external",
                    "storage_path": str(external_path),
                },
            ],
        )
