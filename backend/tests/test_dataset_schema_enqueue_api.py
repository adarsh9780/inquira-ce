from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.v1.api import datasets as datasets_api


@pytest.mark.asyncio
async def test_enqueue_dataset_schema_regeneration_marks_dataset_queued_and_calls_service(monkeypatch):
    timestamp = datetime(2026, 5, 18, 12, 0, 0)
    dataset = SimpleNamespace(
        id=1,
        workspace_id="ws-1",
        source_path="/tmp/demo.csv",
        table_name="demo__1234",
        row_count=10,
        file_type="csv",
        schema_status="ready",
        schema_error_message=None,
        schema_updated_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )
    captured = {}

    async def fake_workspace(_session, _workspace_id, _principal_id):
        return SimpleNamespace(id="ws-1")

    async def fake_dataset(*, session, workspace_id, table_name):
        _ = session
        assert workspace_id == "ws-1"
        assert table_name == "demo__1234"
        return dataset

    class FakeSchemaGenerationService:
        async def enqueue_dataset_schema_generation(self, *, principal_id: str, workspace_id: str, table_name: str) -> None:
            captured["principal_id"] = principal_id
            captured["workspace_id"] = workspace_id
            captured["table_name"] = table_name
            dataset.schema_status = "queued"
            dataset.schema_error_message = None

    monkeypatch.setattr(datasets_api.WorkspaceRepository, "get_by_id", fake_workspace)
    monkeypatch.setattr(datasets_api.DatasetRepository, "get_for_workspace_table", fake_dataset)

    response = await datasets_api.enqueue_workspace_dataset_schema_regeneration(
        workspace_id="ws-1",
        table_name="demo__1234",
        session=SimpleNamespace(),
        current_user=SimpleNamespace(id="principal-1"),
        dataset_schema_generation_service=FakeSchemaGenerationService(),
    )

    assert captured == {
        "principal_id": "principal-1",
        "workspace_id": "ws-1",
        "table_name": "demo__1234",
    }
    assert response.schema_status == "queued"
