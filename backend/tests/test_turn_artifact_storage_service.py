from __future__ import annotations

import json
from pathlib import Path
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

    async def fake_materialize_workspace_artifacts_via_kernel(self, workspace_id, specs):
        _ = self
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
        "app.v1.services.turn_artifact_storage_service.ScratchpadRuntimeAdapter.materialize_workspace_artifacts",
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
    dataframe_path = artifacts_dir / "summary_df__df-1.parquet"
    figure_path = artifacts_dir / "sales_chart__fig-1.json"

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
async def test_persist_turn_artifacts_uses_kernel_metadata_lookup_when_payload_missing(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-2"
    (workspace_dir / "scratchpad").mkdir(parents=True, exist_ok=True)
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
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.ArtifactScratchpadStore.get_artifact",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("scratchpad metadata lookup should not run")),
    )

    async def fake_materialize_workspace_artifacts_via_kernel(self, workspace_id, specs):
        _ = self
        assert workspace_id == "workspace-2"
        for spec in specs:
            target = Path(spec["storage_path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"figure": {"data": [1], "layout": {}}}), encoding="utf-8")
        return [{"artifact_id": "fig-2", "size_bytes": 39}]

    async def fake_get_workspace_artifact_metadata_via_kernel(self, workspace_id, artifact_id):
        _ = self
        assert workspace_id == "workspace-2"
        assert artifact_id == "fig-2"
        return {
            "artifact_id": "fig-2",
            "kind": "figure",
            "logical_name": "trend_chart",
            "payload": {"figure": {"data": [1], "layout": {}}},
            "created_at": "2026-05-18T04:00:00+00:00",
        }

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.ScratchpadRuntimeAdapter.materialize_workspace_artifacts",
        fake_materialize_workspace_artifacts_via_kernel,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.ScratchpadRuntimeAdapter.get_workspace_artifact_metadata",
        fake_get_workspace_artifact_metadata_via_kernel,
    )

    rows = await TurnArtifactStorageService.persist_turn_artifacts(
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
            },
        ],
    )

    assert rows[0]["payload"]["figure"]["data"] == [1]
    assert rows[0]["artifact_id"] == "trend_chart__fig-2"
    assert rows[0]["source_artifact_id"] == "fig-2"
    assert rows[0]["display_name"] == "Trend Chart"
    assert captured["items"][0]["payload"]["figure"]["data"] == [1]


@pytest.mark.asyncio
async def test_persist_turn_artifacts_skips_dataframe_when_kernel_export_missing(monkeypatch, tmp_path) -> None:
    workspace_dir = tmp_path / "workspace-3"
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
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("scratchpad dataframe lookup should not run")),
    )

    async def fake_materialize_workspace_artifacts_via_kernel(self, workspace_id, specs):
        _ = (self, workspace_id, specs)
        return []

    async def fake_get_workspace_artifact_metadata_via_kernel(self, workspace_id, artifact_id):
        _ = self
        assert workspace_id == "workspace-3"
        assert artifact_id == "df-3"
        return {
            "artifact_id": "df-3",
            "kind": "dataframe",
            "logical_name": "summary_df",
            "table_name": "art_df_3",
        }

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.ScratchpadRuntimeAdapter.materialize_workspace_artifacts",
        fake_materialize_workspace_artifacts_via_kernel,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_storage_service.ScratchpadRuntimeAdapter.get_workspace_artifact_metadata",
        fake_get_workspace_artifact_metadata_via_kernel,
    )

    rows = await TurnArtifactStorageService.persist_turn_artifacts(
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
            },
        ],
    )

    assert rows == []
    assert captured["items"] == []
    assert captured["workspace_id"] == "workspace-3"
