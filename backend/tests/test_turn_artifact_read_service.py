from __future__ import annotations

import json
from types import SimpleNamespace

import duckdb
import pytest

from app.v1.services.turn_artifact_read_service import TurnArtifactReadService


@pytest.mark.asyncio
async def test_turn_artifact_read_service_reads_parquet_metadata_and_rows(monkeypatch, tmp_path) -> None:
    parquet_path = tmp_path / "summary.parquet"
    con = duckdb.connect()
    try:
        escaped_path = str(parquet_path).replace("'", "''")
        con.execute(
            f"COPY (SELECT 10 AS amount, 'north' AS region UNION ALL SELECT 5, 'south') TO '{escaped_path}' (FORMAT PARQUET)"
        )
    finally:
        con.close()

    row = SimpleNamespace(
        id="row-1",
        artifact_id="artifact-1",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        logical_name="summary_df",
        kind="dataframe",
        payload_format="parquet",
        storage_path=str(parquet_path),
        created_at=SimpleNamespace(isoformat=lambda: "2026-05-17T00:00:00+00:00"),
        status="active",
    )

    async def fake_get_for_workspace(session, *, workspace_id, artifact_id, statuses=("active",)):
        _ = (session, workspace_id, artifact_id, statuses)
        return row

    async def fake_list_for_workspace(session, workspace_id, *, kind=None, statuses=("active",)):
        _ = (session, workspace_id, kind, statuses)
        return [row]

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.get_for_workspace",
        fake_get_for_workspace,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.list_for_workspace",
        fake_list_for_workspace,
    )

    metadata = await TurnArtifactReadService.get_workspace_artifact(
        SimpleNamespace(),
        workspace_id="workspace-1",
        artifact_id="artifact-1",
    )
    rows = await TurnArtifactReadService.get_dataframe_rows(
        SimpleNamespace(),
        workspace_id="workspace-1",
        artifact_id="artifact-1",
        offset=0,
        limit=100,
    )
    summaries = await TurnArtifactReadService.list_workspace_artifacts(
        SimpleNamespace(),
        workspace_id="workspace-1",
    )

    assert metadata["row_count"] == 2
    assert metadata["schema"][0]["name"] == "amount"
    assert rows["row_count"] == 2
    assert rows["rows"][0]["amount"] == 10
    assert summaries[0]["logical_name"] == "summary_df"


@pytest.mark.asyncio
async def test_turn_artifact_read_service_delete_removes_file_and_manifest_entry(monkeypatch, tmp_path) -> None:
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text('{"figure": {"data": []}}', encoding="utf-8")
    manifest_path = tmp_path / "turn.json"
    manifest_path.write_text(
        json.dumps({"artifacts": [{"artifact_id": "artifact-1"}, {"artifact_id": "artifact-2"}]}),
        encoding="utf-8",
    )
    turn = SimpleNamespace(
        artifact_summary_json=json.dumps([{"artifact_id": "artifact-1"}, {"artifact_id": "artifact-2"}]),
        manifest_path=str(manifest_path),
    )
    row = SimpleNamespace(
        id="row-1",
        artifact_id="artifact-1",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        storage_path=str(artifact_path),
    )

    async def fake_get_for_workspace(session, *, workspace_id, artifact_id, statuses=("active",)):
        _ = (session, workspace_id, artifact_id, statuses)
        return row

    async def fake_delete_by_id(session, artifact_row_id):
        _ = (session, artifact_row_id)
        return None

    async def fake_get_turn(session, turn_id):
        _ = (session, turn_id)
        return turn

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.get_for_workspace",
        fake_get_for_workspace,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.delete_by_id",
        fake_delete_by_id,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.ConversationRepository.get_turn",
        fake_get_turn,
    )

    committed = {"value": False}

    async def fake_commit():
        committed["value"] = True

    session = SimpleNamespace(commit=fake_commit)
    deleted = await TurnArtifactReadService.delete_workspace_artifact(
        session,
        workspace_id="workspace-1",
        artifact_id="artifact-1",
    )

    updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert deleted is True
    assert artifact_path.exists() is False
    assert committed["value"] is True
    assert json.loads(turn.artifact_summary_json) == [{"artifact_id": "artifact-2"}]
    assert updated_manifest["artifacts"] == [{"artifact_id": "artifact-2"}]


@pytest.mark.asyncio
async def test_turn_artifact_read_service_prefers_kernel_usage_for_legacy_scratchpad(monkeypatch, tmp_path) -> None:
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text('{"figure": {"data": []}}', encoding="utf-8")
    row = SimpleNamespace(
        id="row-1",
        artifact_id="artifact-1",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        logical_name="chart",
        kind="figure",
        payload_format="json",
        storage_path=str(artifact_path),
        created_at=SimpleNamespace(isoformat=lambda: "2026-05-17T00:00:00+00:00"),
        status="active",
    )

    async def fake_list_for_workspace(session, workspace_id, *, kind=None, statuses=("active",)):
        _ = (session, workspace_id, kind, statuses)
        return [row]

    async def fake_kernel_usage(self, workspace_id: str):
        _ = self
        assert workspace_id == "workspace-1"
        return {"duckdb_bytes": 128, "figure_count": 3}

    def fail_if_called(*args, **kwargs):
        _ = (args, kwargs)
        raise AssertionError("scratchpad usage fallback should not be used when kernel usage succeeds")

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.list_for_workspace",
        fake_list_for_workspace,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.ScratchpadRuntimeAdapter.get_workspace_artifact_usage",
        fake_kernel_usage,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.ArtifactScratchpadStore.get_workspace_artifact_usage",
        fail_if_called,
    )

    usage = await TurnArtifactReadService.get_workspace_artifact_usage(
        SimpleNamespace(),
        workspace_id="workspace-1",
        workspace_duckdb_path=str(tmp_path / "workspace.duckdb"),
    )

    assert usage == {
        "duckdb_bytes": artifact_path.stat().st_size + 128,
        "figure_count": 4,
    }
