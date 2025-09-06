from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from .auth import get_current_user, get_app_config
from ..database import get_user_settings, save_user_settings
from ..config_models import AppConfig

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

router = APIRouter(tags=["Settings"])

# Response models for individual fields
class DataPathResponse(BaseModel):
    data_path: Optional[str] = None

class ContextResponse(BaseModel):
    context: Optional[str] = None

class ApiKeyResponse(BaseModel):
    api_key: Optional[str] = None


# Request models for setting values
class DataPathRequest(BaseModel):
    data_path: str = Field(description="Path to the data file")

class ContextRequest(BaseModel):
    context: str = Field(description="Context about the data domain")

class ApiKeyRequest(BaseModel):
    api_key: str = Field(description="Google Gemini API key")


# Full settings response
class SettingsResponse(BaseModel):
    data_path: Optional[str] = None
    context: Optional[str] = None
    api_key: Optional[str] = None



# SET endpoints
@router.put("/settings/set/data_path")
async def set_data_path(
    request: DataPathRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the data file path"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    user_settings["data_path"] = request.data_path
    success = save_user_settings(user_id, user_settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save data path")

    # Update app_state
    app_state.data_path = request.data_path

    return {"message": "Data path updated successfully", "data_path": request.data_path}

@router.put("/settings/set/context")
async def set_context(
    request: ContextRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the context for schema generation"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    user_settings["context"] = request.context
    success = save_user_settings(user_id, user_settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save context")

    # Update app_state
    app_state.context = request.context

    return {"message": "Context updated successfully", "context": request.context}

@router.put("/settings/set/api_key")
async def set_apikey(
    request: ApiKeyRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the API key"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    user_settings["api_key"] = request.api_key
    success = save_user_settings(user_id, user_settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save API key")

    # Update app_state and try to initialize LLM service
    app_state.api_key = request.api_key
    try:
        from ..llm_service import LLMService
        app_state.llm_service = LLMService(api_key=request.api_key)
        app_state.llm_initialized = True
        status = "initialized"
    except Exception:
        app_state.llm_service = None
        app_state.llm_initialized = False
        status = "saved"

    return {"message": "API key updated successfully", "status": status}

# VIEW endpoints for individual fields
@router.get("/settings/view/data_path", response_model=DataPathResponse)
async def view_data_path(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """View the current data file path"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    # Load into app_state if needed
    if user_settings.get("data_path"):
        app_state.data_path = user_settings["data_path"]

    return DataPathResponse(data_path=user_settings.get("data_path"))

@router.get("/settings/view/context", response_model=ContextResponse)
async def view_context(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """View the current context"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    # Load into app_state if needed
    if user_settings.get("context"):
        app_state.context = user_settings["context"]

    return ContextResponse(context=user_settings.get("context"))

@router.get("/settings/view/api_key", response_model=ApiKeyResponse)
async def view_apikey(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """View the current API key"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    # Load into app_state if needed
    if user_settings.get("api_key"):
        app_state.api_key = user_settings["api_key"]
        # Try to initialize LLM service
        try:
            from ..llm_service import LLMService
            app_state.llm_service = LLMService(api_key=user_settings["api_key"])
            app_state.llm_initialized = True
        except Exception:
            app_state.llm_service = None
            app_state.llm_initialized = False

    return ApiKeyResponse(api_key=user_settings.get("api_key"))

# VIEW ALL endpoint
@router.get("/settings/view", response_model=SettingsResponse)
async def view_all_settings(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state),
    config = Depends(get_app_config)
):
    """View all settings"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    # Load settings into app_state
    if user_settings.get("data_path"):
        app_state.data_path = user_settings["data_path"]
    if user_settings.get("context"):
        app_state.context = user_settings["context"]
    if user_settings.get("api_key"):
        app_state.api_key = user_settings["api_key"]
        # Try to initialize LLM service
        try:
            from ..llm_service import LLMService
            app_state.llm_service = LLMService(api_key=user_settings["api_key"])
            app_state.llm_initialized = True
        except Exception:
            app_state.llm_service = None
            app_state.llm_initialized = False

    return SettingsResponse(
        data_path=user_settings.get("data_path"),
        context=user_settings.get("context"),
        api_key=user_settings.get("api_key")
    )


def load_user_settings_to_app_state(user_id: str, app_state):
    """
    Load user settings from database into app_state for global access
    Only loads if user has existing settings to avoid overwriting None values for new users
    """
    user_settings = get_user_settings(user_id)

    # Check if schema_path is missing but schema exists for the data_path
    if (user_settings.get("data_path") and
        not user_settings.get("schema_path")):
        from ..schema_storage import load_schema, get_schema_filename, get_user_schema_dir
        schema_file = load_schema(user_id, user_settings["data_path"])
        if schema_file:
            # Schema exists, update settings with the path
            schema_dir = get_user_schema_dir(user_id)
            filename = get_schema_filename(user_settings["data_path"])
            schema_path = str(schema_dir / filename)
            user_settings["schema_path"] = schema_path
            # Save the updated settings
            save_user_settings(user_id, user_settings)

    # Only load settings into app_state if user has existing settings
    if user_settings and any(user_settings.values()):
        # Load settings into app_state
        if user_settings.get("api_key"):
            app_state.api_key = user_settings["api_key"]
            # Try to initialize LLM service if API key is available
            try:
                from ..llm_service import LLMService
                app_state.llm_service = LLMService(api_key=user_settings["api_key"])
                app_state.llm_initialized = True
            except Exception:
                app_state.llm_service = None
                app_state.llm_initialized = False

        if user_settings.get("data_path"):
            app_state.data_path = user_settings["data_path"]
        if user_settings.get("schema_path"):
            app_state.schema_path = user_settings["schema_path"]
        if user_settings.get("context"):
            app_state.context = user_settings["context"]

    return user_settings