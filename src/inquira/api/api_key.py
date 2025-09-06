from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from ..llm_service import LLMService

router = APIRouter(tags=["API Key"])

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

class APIKeyRequest(BaseModel):
    api_key: str = Field(description="Your Google Gemini API key for accessing the LLM service")

@router.post("/set-api-key")
async def set_api_key(
    request: APIKeyRequest,
    app_state = Depends(get_app_state)
):
    """
    Set the API key for LLM service
    """
    app_state.api_key = request.api_key

    # Clear other settings when API key is set via this endpoint
    # (they will be loaded from database when needed)
    if hasattr(app_state, 'data_path'):
        delattr(app_state, 'data_path')
    if hasattr(app_state, 'schema_path'):
        delattr(app_state, 'schema_path')
    if hasattr(app_state, 'context'):
        delattr(app_state, 'context')

    # Try to initialize LLM service with the new API key
    try:
        app_state.llm_service = LLMService(api_key=request.api_key)
        app_state.llm_initialized = True
        return {"message": "API key set successfully", "status": "initialized"}
    except Exception as e:
        app_state.llm_service = None
        app_state.llm_initialized = False
        raise HTTPException(
            status_code=400,
            detail=f"Invalid API key: {str(e)}"
        )