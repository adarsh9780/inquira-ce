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
    assert metadata["display_name"] == "Summary Df"
    assert rows["row_count"] == 2
    assert rows["rows"][0]["amount"] == 10
    assert rows["display_name"] == "Summary Df"
    assert summaries[0]["logical_name"] == "summary_df"
    assert summaries[0]["display_name"] == "Summary Df"


@pytest.mark.asyncio
async def test_turn_artifact_read_service_uses_turn_scope_for_duplicate_artifact_ids(monkeypatch, tmp_path) -> None:
    turn_one_path = tmp_path / "turn-one.parquet"
    turn_two_path = tmp_path / "turn-two.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"COPY (SELECT 1 AS value) TO '{str(turn_one_path).replace("'", "''")}' (FORMAT PARQUET)"
        )
        con.execute(
            f"COPY (SELECT 2 AS value) TO '{str(turn_two_path).replace("'", "''")}' (FORMAT PARQUET)"
        )
    finally:
        con.close()

    rows_by_turn = {
        "turn-1": SimpleNamespace(
            id="row-1",
            artifact_id="shared-artifact",
            workspace_id="workspace-1",
            conversation_id="conversation-1",
            turn_id="turn-1",
            logical_name="summary",
            kind="dataframe",
            payload_format="parquet",
            storage_path=str(turn_one_path),
            created_at=SimpleNamespace(isoformat=lambda: "2026-05-17T00:00:00+00:00"),
            status="active",
        ),
        "turn-2": SimpleNamespace(
            id="row-2",
            artifact_id="shared-artifact",
            workspace_id="workspace-1",
            conversation_id="conversation-1",
            turn_id="turn-2",
            logical_name="summary",
            kind="dataframe",
            payload_format="parquet",
            storage_path=str(turn_two_path),
            created_at=SimpleNamespace(isoformat=lambda: "2026-05-17T00:01:00+00:00"),
            status="active",
        ),
    }

    async def fake_get_for_turn(session, *, turn_id, artifact_id, statuses=("active",)):
        _ = (session, artifact_id, statuses)
        return rows_by_turn[turn_id]

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.get_for_turn",
        fake_get_for_turn,
    )

    turn_one_rows = await TurnArtifactReadService.get_turn_dataframe_rows(
        SimpleNamespace(),
        turn_id="turn-1",
        artifact_id="shared-artifact",
        offset=0,
        limit=100,
    )
    turn_two_rows = await TurnArtifactReadService.get_turn_dataframe_rows(
        SimpleNamespace(),
        turn_id="turn-2",
        artifact_id="shared-artifact",
        offset=0,
        limit=100,
    )

    assert turn_one_rows["rows"] == [{"value": 1}]
    assert turn_two_rows["rows"] == [{"value": 2}]


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
async def test_turn_artifact_read_service_usage_counts_only_turn_artifact_files(monkeypatch, tmp_path) -> None:
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

    def fail_if_called(*args, **kwargs):
        _ = (args, kwargs)
        raise AssertionError("scratchpad usage fallback should not be used")

    monkeypatch.setattr(
        "app.v1.services.turn_artifact_read_service.TurnArtifactRepository.list_for_workspace",
        fake_list_for_workspace,
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
        "duckdb_bytes": artifact_path.stat().st_size,
        "figure_count": 1,
    }
