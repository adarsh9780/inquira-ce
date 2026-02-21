"""API v1 administrative utilities (guarded/reset)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..core.settings import settings
from ..db.base import Base
from ..db.session import engine
from ..schemas.common import MessageResponse

router = APIRouter(prefix="/admin", tags=["V1 Admin"])


@router.post("/reset", response_model=MessageResponse)
async def reset_everything(token: str):
    """One-time destructive reset for legacy/users/schema data.

    Requires:
      - INQUIRA_ENABLE_RESET=1
      - token matching INQUIRA_RESET_TOKEN
    """
    if not settings.reset_enabled:
        raise HTTPException(status_code=403, detail="Reset command disabled")
    if not settings.reset_token or token != settings.reset_token:
        raise HTTPException(status_code=401, detail="Invalid reset token")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    def _delete_legacy() -> None:
        legacy = Path.home() / ".inquira" / "app.db"
        if legacy.exists():
            legacy.unlink()

    await asyncio.to_thread(_delete_legacy)
    return MessageResponse(message="Reset completed")
