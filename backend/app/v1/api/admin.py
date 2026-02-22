"""API v1 administrative utilities (guarded/reset)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.settings import settings
from ..db.base import Base
from ..db.session import engine
from ..schemas.common import MessageResponse
from ...services.llm_service import LLMService

router = APIRouter(prefix="/admin", tags=["V1 Admin"])


class GeminiTestRequest(BaseModel):
    api_key: str = Field(description="Google Gemini API key to test")


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


@router.post("/test-gemini")
async def test_gemini_api_key(payload: GeminiTestRequest):
    """Validate a Gemini key by issuing a lightweight test request."""
    api_key = (payload.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="Please provide a valid Google Gemini API key to test.")

    try:
        llm_service = LLMService(api_key=api_key)
        llm_service.ask(
            "Hello, please respond with just the word 'OK' to confirm this API key is working.",
            str,
        )
        return {"detail": "API key is valid and working correctly"}
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
        lowered = error_msg.lower()
        if "api_key_invalid" in lowered or "invalid" in lowered:
            raise HTTPException(
                status_code=401,
                detail="The provided API key appears to be invalid. Please check your Google Gemini API key.",
            ) from exc
        if "quota" in lowered or "limit" in lowered:
            raise HTTPException(
                status_code=429,
                detail="Your API key has exceeded its usage quota. Please check your Google Cloud billing and limits.",
            ) from exc
        if "permission" in lowered or "unauthorized" in lowered:
            raise HTTPException(
                status_code=403,
                detail="The API key doesn't have the required permissions to access Google Gemini.",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Error testing API key: {error_msg}") from exc
