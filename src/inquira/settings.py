from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional
from .auth import get_current_user
from .database import get_user_settings, save_user_settings, delete_user_settings

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

router = APIRouter(tags=["Settings"])

class SettingsRequest(BaseModel):
    api_key: str = Field(description="Your Google Gemini API key for accessing the LLM service")
    data_path: str = Field(description="Path to the data directory or file")
    schema_path: Optional[str] = Field(None, description="Optional path to the schema file")
    context: Optional[str] = Field(None, description="Context about the data domain for schema generation")

class SettingsResponse(BaseModel):
    api_key: Optional[str] = None
    data_path: Optional[str] = None
    schema_path: Optional[str] = None
    context: Optional[str] = None


class DeleteSettingsSuccessResponse(BaseModel):
    success: bool = Field(description="Indicates if the operation was successful")
    message: str = Field(description="Human-readable success message")
    details: str = Field(description="Detailed information about the operation")


class DeleteSettingsErrorResponse(BaseModel):
    error: str = Field(description="Error type or code")
    message: str = Field(description="Human-readable error message")


@router.post("/settings/create")
async def create_settings(
    request: SettingsRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """
    Create or update user-specific application settings
    """
    user_id = current_user["user_id"]

    settings_data = {
        "api_key": request.api_key,
        "data_path": request.data_path,
        "schema_path": request.schema_path,
        "context": request.context
    }

    success = save_user_settings(user_id, settings_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings")

    # Store settings in app_state for global access
    app_state.api_key = request.api_key
    app_state.data_path = request.data_path
    app_state.schema_path = request.schema_path
    app_state.context = request.context

    # Try to validate API key and initialize LLM service
    try:
        from .llm_service import LLMService
        app_state.llm_service = LLMService(api_key=request.api_key)
        app_state.llm_initialized = True
        return {"message": "Settings created successfully", "status": "initialized"}
    except Exception as e:
        app_state.llm_service = None
        app_state.llm_initialized = False
        return {"message": "Settings saved, but API key may need verification", "status": "saved"}

@router.get("/settings/view", response_model=SettingsResponse)
async def view_settings(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """
    View current user-specific application settings
    """
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id)

    # Check if schema_path is missing but schema exists for the data_path
    if (user_settings.get("data_path") and
        not user_settings.get("schema_path")):
        from .schema_storage import load_schema, get_schema_filename, get_user_schema_dir
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
    # This ensures new users don't get None values loaded into app_state
    if user_settings and any(user_settings.values()):
        # Load settings into app_state for global access
        if user_settings.get("api_key"):
            app_state.api_key = user_settings["api_key"]
            # Try to initialize LLM service if API key is available
            try:
                from .llm_service import LLMService
                app_state.llm_service = LLMService(api_key=user_settings["api_key"])
                app_state.llm_initialized = True
            except Exception as e:
                app_state.llm_service = None
                app_state.llm_initialized = False

        if user_settings.get("data_path"):
            app_state.data_path = user_settings["data_path"]
        if user_settings.get("schema_path"):
            app_state.schema_path = user_settings["schema_path"]
        if user_settings.get("context"):
            app_state.context = user_settings["context"]

    return SettingsResponse(**user_settings)

@router.delete(
    "/settings/delete",
    response_model=DeleteSettingsSuccessResponse,
    responses={
        200: {"model": DeleteSettingsSuccessResponse},
        500: {"model": DeleteSettingsErrorResponse}
    }
)
async def delete_settings(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Delete all settings for the current user"""
    user_id = current_user["user_id"]

    success = delete_user_settings(user_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=DeleteSettingsErrorResponse(
                error="DatabaseError",
                message="An error occurred while deleting user settings from the database"
            ).model_dump()
        )

    # Clear app_state to remove cached settings
    app_state.api_key = None
    app_state.data_path = None
    app_state.schema_path = None
    app_state.context = None
    app_state.llm_service = None
    app_state.llm_initialized = False

    return DeleteSettingsSuccessResponse(
        success=True,
        message="Settings deleted successfully",
        details="All user settings have been removed from the database and application state has been cleared"
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
        from .schema_storage import load_schema, get_schema_filename, get_user_schema_dir
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
                from .llm_service import LLMService
                app_state.llm_service = LLMService(api_key=user_settings["api_key"])
                app_state.llm_initialized = True
            except Exception as e:
                app_state.llm_service = None
                app_state.llm_initialized = False

        if user_settings.get("data_path"):
            app_state.data_path = user_settings["data_path"]
        if user_settings.get("schema_path"):
            app_state.schema_path = user_settings["schema_path"]
        if user_settings.get("context"):
            app_state.context = user_settings["context"]

    return user_settings