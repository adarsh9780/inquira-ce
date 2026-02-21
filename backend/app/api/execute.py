"""
execute.py — Code Execution API Router

Provides the /execute endpoint for running Python code server-side.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.code_executor import execute_code

router = APIRouter(tags=["execute"])


class ExecuteRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    timeout: int = Field(60, ge=1, le=300, description="Max execution time in seconds")


class ExecuteResponse(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    result: object | None = None
    result_type: str | None = None


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code_endpoint(request: ExecuteRequest):
    """Execute Python code on the server and return results."""
    result = await execute_code(
        code=request.code,
        timeout=request.timeout,
    )
    return ExecuteResponse(**result)
