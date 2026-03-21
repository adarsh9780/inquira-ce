"""Shared-secret protected internal runtime endpoints for the agent service."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..repositories.workspace_repository import WorkspaceRepository
from .runtime import ExecuteRequest, ExecuteResponse, _execute_workspace_code_impl

router = APIRouter(
    prefix="/internal/agent",
    tags=["V1 Agent Runtime Internal"],
)


def _require_agent_runtime_auth(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> None:
    configured_secret = str(os.getenv("INQUIRA_AGENT_SHARED_SECRET") or "").strip()
    if not configured_secret:
        raise HTTPException(status_code=503, detail="Agent runtime auth is not configured.")

    header = str(authorization or "").strip()
    expected = f"Bearer {configured_secret}"
    if header != expected:
        raise HTTPException(status_code=401, detail="Invalid agent runtime authorization.")


@router.post(
    "/workspaces/{workspace_id}/execute",
    response_model=ExecuteResponse,
    include_in_schema=False,
    dependencies=[Depends(_require_agent_runtime_auth)],
)
async def execute_workspace_code_for_agent(
    workspace_id: str,
    payload: ExecuteRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
):
    workspace = await WorkspaceRepository.get_any_by_id(session, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return await _execute_workspace_code_impl(
        workspace_id=workspace_id,
        workspace_duckdb_path=str(getattr(workspace, "duckdb_path", "") or ""),
        payload=payload,
    )
