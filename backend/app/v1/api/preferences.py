"""API v1 user preferences and keychain-backed API key routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..repositories.preferences_repository import PreferencesRepository
from ..schemas.common import MessageResponse
from ..schemas.preferences import (
    ApiKeyUpdateRequest,
    PreferencesResponse,
    PreferencesUpdateRequest,
)
from ..services.secret_storage_service import SecretStorageService
from .deps import get_current_user

router = APIRouter(prefix="/preferences", tags=["V1 Preferences"])


def _to_response(prefs, api_key_present: bool) -> PreferencesResponse:
    return PreferencesResponse(
        selected_model=prefs.selected_model,
        schema_context=prefs.schema_context,
        allow_schema_sample_values=bool(prefs.allow_schema_sample_values),
        chat_overlay_width=float(prefs.chat_overlay_width),
        is_sidebar_collapsed=bool(prefs.is_sidebar_collapsed),
        hide_shortcuts_modal=bool(prefs.hide_shortcuts_modal),
        active_workspace_id=prefs.active_workspace_id,
        active_dataset_path=prefs.active_dataset_path,
        active_table_name=prefs.active_table_name,
        api_key_present=api_key_present,
    )


@router.get("", response_model=PreferencesResponse)
async def get_preferences(
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    await session.commit()
    key_present = bool(SecretStorageService.get_api_key(current_user.id))
    return _to_response(prefs, key_present)


@router.put("", response_model=PreferencesResponse)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)

    if payload.selected_model is not None:
        prefs.selected_model = payload.selected_model
    if payload.schema_context is not None:
        prefs.schema_context = payload.schema_context
    if payload.allow_schema_sample_values is not None:
        prefs.allow_schema_sample_values = payload.allow_schema_sample_values
    if payload.chat_overlay_width is not None:
        prefs.chat_overlay_width = payload.chat_overlay_width
    if payload.is_sidebar_collapsed is not None:
        prefs.is_sidebar_collapsed = payload.is_sidebar_collapsed
    if payload.hide_shortcuts_modal is not None:
        prefs.hide_shortcuts_modal = payload.hide_shortcuts_modal

    # Allow explicit clear by empty string; keep None as "no change" for workspace id.
    if payload.active_workspace_id is not None:
        prefs.active_workspace_id = payload.active_workspace_id or None
    if payload.active_dataset_path is not None:
        prefs.active_dataset_path = payload.active_dataset_path or None
    if payload.active_table_name is not None:
        prefs.active_table_name = payload.active_table_name or None

    await session.commit()
    key_present = bool(SecretStorageService.get_api_key(current_user.id))
    return _to_response(prefs, key_present)


@router.put("/api-key", response_model=MessageResponse)
async def set_api_key(
    payload: ApiKeyUpdateRequest,
    current_user=Depends(get_current_user),
):
    api_key = (payload.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    try:
        SecretStorageService.set_api_key(current_user.id, api_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to persist API key in OS keychain.") from exc
    return MessageResponse(message="API key saved to OS keychain.")


@router.delete("/api-key", response_model=MessageResponse)
async def delete_api_key(
    current_user=Depends(get_current_user),
):
    try:
        SecretStorageService.delete_api_key(current_user.id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to remove API key from OS keychain.") from exc
    return MessageResponse(message="API key removed from OS keychain.")
