from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..services.llm_service import LLMService

router = APIRouter(tags=["API Testing"])

class GeminiTestRequest(BaseModel):
    api_key: str = Field(description="Google Gemini API key to test")

class GeminiTestResponse(BaseModel):
    success: bool
    message: str
    error_message: Optional[str] = None

@router.post("/api/test-gemini")
async def verify_gemini_api_key(request: GeminiTestRequest):
    """
    Test a Google Gemini API key by making a simple test request.

    This endpoint validates that the provided API key is working
    by sending a simple test message to Gemini.

    Returns:
    - 200 OK: API key is valid
    - 400 Bad Request: Missing or empty API key
    - 401 Unauthorized: Invalid API key
    - 403 Forbidden: Insufficient permissions
    - 429 Too Many Requests: Quota exceeded
    - 500 Internal Server Error: Other errors
    """
    api_key = request.api_key

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid Google Gemini API key to test."
        )

    try:
        # Initialize LLM service with user's API key
        llm_service = LLMService(api_key=api_key)

        # Make a simple test request
        test_prompt = "Hello, please respond with just the word 'OK' to confirm this API key is working."

        response = llm_service.ask(test_prompt, str)  # Simple string response for testing

        # If we get here, the API key is working
        return {"detail": "API key is valid and working correctly"}

    except Exception as e:
        error_msg = str(e)

        # Provide more user-friendly error messages with appropriate HTTP status codes
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="The provided API key appears to be invalid. Please check your Google Gemini API key."
            )
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="Your API key has exceeded its usage quota. Please check your Google Cloud billing and limits."
            )
        elif "permission" in error_msg.lower() or "unauthorized" in error_msg.lower():
            raise HTTPException(
                status_code=403,
                detail="The API key doesn't have the required permissions to access Google Gemini. Please check your API key configuration."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error testing API key: {error_msg}"
            )
