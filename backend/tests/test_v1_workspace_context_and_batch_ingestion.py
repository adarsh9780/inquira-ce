from __future__ import annotations

from pathlib import Path
from datetime import datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.v1.schemas.dataset import DatasetBatchAddRequest, DatasetIngestionJobResponse
from app.v1.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceRenameRequest,
    WorkspaceResponse,
    WorkspaceSummaryResponse,
)
from app.v1.services.dataset_ingestion_service import _read_items


def _migration_config(db_path: Path, db_role: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.attributes["inquira_db_role"] = db_role
    return cfg


def test_workspace_context_migration_adds_context_and_ingestion_jobs(tmp_path) -> None:
    db_path = tmp_path / "appdata_v1.db"
    command.upgrade(_migration_config(db_path, "appdata"), "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        workspace_columns = {column["name"] for column in inspector.get_columns("v1_workspaces")}
        ingestion_columns = {
            column["name"] for column in inspector.get_columns("v1_dataset_ingestion_jobs")
        }
        assert "schema_context" in workspace_columns
        assert {
            "id",
            "owner_principal_id",
            "workspace_id",
            "status",
            "total_count",
            "completed_count",
            "failed_count",
            "items_json",
            "error_message",
        }.issubset(ingestion_columns)
    finally:
        engine.dispose()


def test_workspace_schemas_include_shared_schema_context() -> None:
    create_payload = WorkspaceCreateRequest(name="Finance", schema_context="Retail terms")
    update_payload = WorkspaceRenameRequest(schema_context="Updated terms")
    timestamp = datetime(2026, 5, 3, 12, 0, 0)

    response = WorkspaceResponse(
        id="ws-1",
        name=create_payload.name,
        duckdb_path="/tmp/workspace.db",
        schema_context=create_payload.schema_context,
        is_active=True,
        created_at=timestamp,
        updated_at=timestamp,
    )
    summary = WorkspaceSummaryResponse(
        id="ws-1",
        name="Finance",
        schema_context=update_payload.schema_context or "",
        is_active=True,
        table_count=0,
        table_names=[],
        conversation_count=0,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert create_payload.schema_context == "Retail terms"
    assert update_payload.name is None
    assert response.schema_context == "Retail terms"
    assert summary.schema_context == "Updated terms"


def test_dataset_batch_ingestion_contract_and_item_json_helpers() -> None:
    request = DatasetBatchAddRequest(source_paths=["/tmp/a.csv", "/tmp/b.csv"])
    timestamp = datetime(2026, 5, 3, 12, 0, 0)
    response = DatasetIngestionJobResponse(
        job_id="job-1",
        workspace_id="ws-1",
        status="queued",
        total_count=2,
        completed_count=0,
        failed_count=0,
        items=[
            {"source_path": "/tmp/a.csv", "status": "queued"},
            {"source_path": "/tmp/b.csv", "status": "queued"},
        ],
        error_message=None,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert request.source_paths == ["/tmp/a.csv", "/tmp/b.csv"]
    assert response.total_count == 2
    assert _read_items(response.model_dump_json()) == []
    assert _read_items('[{"source_path": "/tmp/a.csv", "status": "queued"}]')[0]["status"] == "queued"


def test_batch_ingestion_service_processes_items_sequentially() -> None:
    service_path = Path(__file__).resolve().parents[1] / "app/v1/services/dataset_ingestion_service.py"
    source = service_path.read_text(encoding="utf-8")

    assert "self._ingest_lock = asyncio.Lock()" in source
    assert "for index, item in enumerate(items):" in source
    assert "async with self._ingest_lock:" in source
    assert "await DatasetService.add_dataset(" in source
    assert "asyncio.gather" not in source
