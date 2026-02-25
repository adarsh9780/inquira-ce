from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..services.llm_service import LLMService

router = APIRouter(tags=["API Testing"])

class GeminiTestRequest(BaseModel):
    api_key: str = Field(description="OpenRouter API key to test")
    model: str | None = Field(
        default=None, description="Optional model identifier to validate against."
    )

class GeminiTestResponse(BaseModel):
    success: bool
    message: str
    error_message: Optional[str] = None

@router.post("/api/test-gemini")
async def verify_gemini_api_key(request: GeminiTestRequest):
    """
    Test an OpenRouter-compatible API key by making a simple test request.

    This endpoint validates that the provided API key is working
    by sending a simple test message to the configured provider.

    Returns:
    - 200 OK: API key is valid
    - 400 Bad Request: Missing or empty API key
    - 401 Unauthorized: Invalid API key
    - 403 Forbidden: Insufficient permissions
    - 429 Too Many Requests: Quota exceeded
    - 500 Internal Server Error: Other errors
    """
    api_key = request.api_key
    model = (request.model or "").strip()

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid API key to test."
        )

    try:
        # Initialize LLM service with user's API key
        llm_service = LLMService(api_key=api_key, model=model or "google/gemini-2.5-flash")

        # Make a simple test request
        test_prompt = "Hello, please respond with just the word 'OK' to confirm this API key is working."

        llm_service.ask(test_prompt, str, max_tokens=8)  # Keep probe lightweight

        # If we get here, the API key is working
        return {"detail": "API key is valid and working correctly"}

    except HTTPException as e:
        status_code = int(e.status_code)
        error_msg = str(e.detail)
        if status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="The provided API key appears to be invalid. Please check your API key."
            )
        elif status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="Your API key has exceeded its usage quota. Please check your provider billing and limits."
            )
        elif status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="The API key doesn't have the required permissions for this provider/model. Please check your key configuration."
            )
        elif status_code in {400, 404}:
            raise HTTPException(
                status_code=400,
                detail=f"Provider rejected model '{model or 'google/gemini-2.5-flash'}'. Pick another model or verify provider access."
            )
        else:
            raise HTTPException(
                status_code=status_code,
                detail=f"Error testing API key: {error_msg}"
            )
    except Exception as e:
        error_msg = str(e)

        # Provide more user-friendly error messages with appropriate HTTP status codes
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="The provided API key appears to be invalid. Please check your API key."
            )
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="Your API key has exceeded its usage quota. Please check your provider billing and limits."
            )
        elif "permission" in error_msg.lower() or "unauthorized" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail="The API key doesn't have the required permissions for this provider/model. Please check your key configuration."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error testing API key: {error_msg}"
            )
