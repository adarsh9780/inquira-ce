from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.api import conversations as conversation_api


async def _fake_turn_access(*, session, principal_id, conversation_id, turn_id):
    _ = (session, principal_id)
    return SimpleNamespace(id=turn_id, conversation_id=conversation_id)


@pytest.mark.asyncio
async def test_turn_artifact_routes_list_metadata_rows_and_delete(monkeypatch) -> None:
    monkeypatch.setattr(conversation_api, "_ensure_turn_access", _fake_turn_access)

    async def fake_list(session, *, turn_id, kind=None):
        _ = session
        assert turn_id == "turn-1"
        assert kind == "dataframe"
        return [
            {
                "artifact_id": "artifact-1",
                "logical_name": "summary",
                "display_name": "Summary",
                "kind": "dataframe",
                "row_count": 1,
                "schema": [{"name": "value", "dtype": "INTEGER"}],
                "created_at": "2026-05-17T00:00:00+00:00",
                "status": "active",
            }
        ]

    async def fake_metadata(session, *, turn_id, artifact_id):
        _ = session
        assert turn_id == "turn-1"
        assert artifact_id == "artifact-1"
        return {
            "artifact_id": "artifact-1",
            "run_id": "turn-1",
            "workspace_id": "workspace-1",
            "logical_name": "summary",
            "display_name": "Summary",
            "kind": "dataframe",
            "pointer": "/tmp/summary.parquet",
            "table_name": None,
            "schema": [{"name": "value", "dtype": "INTEGER"}],
            "row_count": 1,
            "payload": None,
            "created_at": "2026-05-17T00:00:00+00:00",
            "expires_at": "",
            "status": "active",
            "error": None,
        }

    async def fake_rows(session, *, turn_id, artifact_id, offset, limit, sort_model=None, filter_model=None, search_text=None):
        _ = session
        assert turn_id == "turn-1"
        assert artifact_id == "artifact-1"
        assert offset == 0
        assert limit == 100
        assert sort_model == [{"colId": "value", "sort": "desc"}]
        assert filter_model == {}
        assert search_text == "north"
        return {
            "artifact_id": "artifact-1",
            "name": "summary",
            "display_name": "Summary",
            "row_count": 1,
            "columns": ["value"],
            "rows": [{"value": 1}],
            "offset": 0,
            "limit": 100,
        }

    async def fake_delete(session, *, turn_id, artifact_id):
        _ = session
        assert turn_id == "turn-1"
        assert artifact_id == "artifact-1"
        return True

    monkeypatch.setattr(conversation_api.TurnArtifactReadService, "list_turn_artifacts", fake_list)
    monkeypatch.setattr(conversation_api.TurnArtifactReadService, "get_turn_artifact", fake_metadata)
    monkeypatch.setattr(conversation_api.TurnArtifactReadService, "get_turn_dataframe_rows", fake_rows)
    monkeypatch.setattr(conversation_api.TurnArtifactReadService, "delete_turn_artifact", fake_delete)

    current_user = SimpleNamespace(id="user-1")
    listed = await conversation_api.list_turn_artifacts(
        conversation_id="conversation-1",
        turn_id="turn-1",
        kind="dataframe",
        session=object(),
        current_user=current_user,
    )
    metadata = await conversation_api.get_turn_artifact_metadata(
        conversation_id="conversation-1",
        turn_id="turn-1",
        artifact_id="artifact-1",
        session=object(),
        current_user=current_user,
    )
    rows = await conversation_api.get_turn_artifact_rows(
        conversation_id="conversation-1",
        turn_id="turn-1",
        artifact_id="artifact-1",
        offset=0,
        limit=100,
        sort_model='[{"colId":"value","sort":"desc"}]',
        filter_model="{}",
        search="north",
        session=object(),
        current_user=current_user,
    )
    deleted = await conversation_api.delete_turn_artifact(
        conversation_id="conversation-1",
        turn_id="turn-1",
        artifact_id="artifact-1",
        session=object(),
        current_user=current_user,
    )

    assert listed.total == 1
    assert listed.artifacts[0].artifact_id == "artifact-1"
    assert metadata.artifact_id == "artifact-1"
    assert rows.rows == [{"value": 1}]
    assert deleted.deleted is True


@pytest.mark.asyncio
async def test_turn_artifact_routes_return_404_for_missing_turn_artifact(monkeypatch) -> None:
    monkeypatch.setattr(conversation_api, "_ensure_turn_access", _fake_turn_access)

    async def fake_metadata(session, *, turn_id, artifact_id):
        _ = (session, turn_id, artifact_id)
        return None

    monkeypatch.setattr(conversation_api.TurnArtifactReadService, "get_turn_artifact", fake_metadata)

    with pytest.raises(conversation_api.HTTPException) as exc:
        await conversation_api.get_turn_artifact_metadata(
            conversation_id="conversation-1",
            turn_id="turn-1",
            artifact_id="missing",
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Turn artifact not found"
