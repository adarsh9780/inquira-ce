from types import SimpleNamespace

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
async def test_add_dataset_returns_explicit_error_when_kernel_is_inactive(monkeypatch, tmp_path):
    source = tmp_path / "demo.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()

    user = SimpleNamespace(id="user-1")
    workspace = SimpleNamespace(duckdb_path=str(workspace_db))

    async def fake_get_by_id(session, workspace_id, user_id):
        _ = (session, workspace_id, user_id)
        return workspace

    async def fake_ensure_kernel(_workspace_id, _operation_name):
        raise RuntimeError(
            "Loading a dataset requires an active workspace kernel because Inquira now reuses the "
            "kernel-owned DuckDB connections for workspace data and artifacts. Start or restart the "
            "workspace kernel, wait for Kernel Ready, then try again."
        )

    monkeypatch.setattr(
        dataset_service_module.WorkspaceRepository,
        "get_by_id",
        fake_get_by_id,
    )
    monkeypatch.setattr(dataset_service_module, "ensure_workspace_kernel_active", fake_ensure_kernel)

    with pytest.raises(HTTPException) as exc:
        await DatasetService.add_dataset(
            session=_Session(),
            user=user,
            workspace_id="ws-1",
            source_path=str(source),
        )
    assert exc.value.status_code == 409
    assert "active workspace kernel" in str(exc.value.detail).lower()
