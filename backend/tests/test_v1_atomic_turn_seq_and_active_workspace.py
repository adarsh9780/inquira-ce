from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase
from app.v1.models import Conversation, Principal, Turn, Workspace
from app.v1.repositories.conversation_repository import ConversationRepository
from app.v1.services.workspace_service import WorkspaceService


def test_atomic_turn_seq_and_active_workspace_migration_adds_columns(tmp_path) -> None:
    db_path = tmp_path / "appdata_v1.db"
    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.attributes["inquira_db_role"] = "appdata"

    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        principal_columns = {column["name"] for column in inspector.get_columns("v1_principals")}
        principal_indexes = {index["name"] for index in inspector.get_indexes("v1_principals")}
        conversation_columns = {column["name"] for column in inspector.get_columns("v1_conversations")}

        assert "active_workspace_id" in principal_columns
        assert "ix_v1_principals_active_workspace_id" in principal_indexes
        assert "next_turn_seq" in conversation_columns
    finally:
        engine.dispose()


@pytest.fixture
async def appdata_session_factory(tmp_path):
    db_path = tmp_path / "atomicity.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_repository_next_seq_no_is_atomic_under_concurrency(appdata_session_factory) -> None:
    async with appdata_session_factory() as session:
        principal = Principal(id="principal-1", username_cached="alice", plan_cached="FREE")
        workspace = Workspace(
            id="ws-1",
            owner_principal_id="principal-1",
            name="Data Lab",
            name_normalized="data lab",
            duckdb_path="/tmp/ws-1/workspace.db",
            is_active=1,
        )
        conversation = Conversation(
            id="conv-1",
            workspace_id="ws-1",
            created_by_principal_id="principal-1",
            title="New Conversation",
        )
        session.add_all([principal, workspace, conversation])
        await session.commit()

    start = asyncio.Event()

    async def _create_turn(index: int) -> int:
        async with appdata_session_factory() as session:
            await start.wait()
            seq_no = await ConversationRepository.next_seq_no(session, "conv-1")
            await ConversationRepository.create_turn(
                session,
                conversation_id="conv-1",
                seq_no=seq_no,
                user_text=f"q-{index}",
                assistant_text="ok",
                tool_events=None,
                metadata=None,
                code_snapshot=None,
            )
            await session.commit()
            return seq_no

    tasks = [asyncio.create_task(_create_turn(index)) for index in range(8)]
    start.set()
    allocated = await asyncio.gather(*tasks)

    assert sorted(allocated) == list(range(1, 9))

    async with appdata_session_factory() as session:
        rows = await session.execute(select(Turn.seq_no).where(Turn.conversation_id == "conv-1"))
        persisted = sorted(int(item[0]) for item in rows.all())
        conversation = await session.get(Conversation, "conv-1")

    assert persisted == list(range(1, 9))
    assert conversation is not None
    assert int(conversation.next_turn_seq) == 9


@pytest.mark.asyncio
async def test_workspace_activation_keeps_single_active_pointer_under_concurrency(
    appdata_session_factory,
    monkeypatch,
) -> None:
    async def fake_stop_terminal_session(**_kwargs):
        return None

    async def fake_reset_workspace_kernel(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "app.v1.services.workspace_service.stop_workspace_terminal_session",
        fake_stop_terminal_session,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.reset_workspace_kernel",
        fake_reset_workspace_kernel,
    )

    async def fake_write_manifest(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceStorageService.write_workspace_manifest",
        fake_write_manifest,
    )

    async with appdata_session_factory() as session:
        principal = Principal(
            id="principal-1",
            username_cached="alice",
            plan_cached="FREE",
            active_workspace_id="ws-1",
        )
        workspace_a = Workspace(
            id="ws-1",
            owner_principal_id="principal-1",
            name="Alpha",
            name_normalized="alpha",
            duckdb_path="/tmp/ws-1/workspace.db",
            is_active=1,
        )
        workspace_b = Workspace(
            id="ws-2",
            owner_principal_id="principal-1",
            name="Beta",
            name_normalized="beta",
            duckdb_path="/tmp/ws-2/workspace.db",
            is_active=0,
        )
        session.add_all([principal, workspace_a, workspace_b])
        await session.commit()

    user = SimpleNamespace(id="principal-1", username="alice")
    start = asyncio.Event()

    async def _activate(workspace_id: str):
        async with appdata_session_factory() as session:
            await start.wait()
            try:
                await WorkspaceService.activate_workspace(
                    session=session,
                    user=user,
                    workspace_id=workspace_id,
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return exc.__class__.__name__

    task_a = asyncio.create_task(_activate("ws-1"))
    task_b = asyncio.create_task(_activate("ws-2"))
    start.set()
    results = await asyncio.gather(task_a, task_b)

    async with appdata_session_factory() as session:
        principal = await session.get(Principal, "principal-1")
        rows = await session.execute(
            select(Workspace.id, Workspace.is_active)
            .where(Workspace.owner_principal_id == "principal-1")
            .order_by(Workspace.id.asc())
        )
        workspace_rows = rows.all()

    assert principal is not None
    active_ids = [workspace_id for workspace_id, is_active in workspace_rows if int(is_active) == 1]
    assert len(active_ids) == 1
    assert principal.active_workspace_id == active_ids[0]
    assert set(results).issubset({"ok", "HTTPException"})
