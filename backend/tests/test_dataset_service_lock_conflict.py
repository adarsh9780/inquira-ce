from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest
from fastapi import HTTPException

from app.v1.services.dataset_service import DatasetService
from app.v1.services import dataset_service as dataset_service_module


class _Result:
    def scalar_one_or_none(self):
        return None


class _Session:
    async def execute(self, *_args, **_kwargs):
        return _Result()

    async def commit(self):
        return None

    async def refresh(self, _item):
        return None


@pytest.mark.asyncio
async def test_add_dataset_returns_409_on_duckdb_lock_conflict(monkeypatch, tmp_path):
    source = tmp_path / "demo.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()

    user = SimpleNamespace(id="user-1")
    workspace = SimpleNamespace(duckdb_path=str(workspace_db))

    async def fake_get_by_id(session, workspace_id, user_id):
        _ = (session, workspace_id, user_id)
        return workspace

    monkeypatch.setattr(
        dataset_service_module.WorkspaceRepository,
        "get_by_id",
        fake_get_by_id,
    )

    def fake_connect(path):
        _ = path
        raise duckdb.IOException("Conflicting lock is held")

    monkeypatch.setattr(dataset_service_module.duckdb, "connect", fake_connect)

    with pytest.raises(HTTPException) as exc:
        await DatasetService.add_dataset(
            session=_Session(),
            user=user,
            workspace_id="ws-1",
            source_path=str(Path(source)),
        )
    assert exc.value.status_code == 409
    assert "currently locked" in str(exc.value.detail).lower()
