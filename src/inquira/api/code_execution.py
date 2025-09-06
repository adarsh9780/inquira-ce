from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Any, Optional

from ..code_whisperer import CodeWhisperer

router = APIRouter(prefix="/execute", tags=["Code Execution"])

class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")

class CodeExecutionResponse(BaseModel):
    result: Optional[Any] = Field(None, description="Execution result")
    output: Optional[str] = Field(None, description="Captured stdout output")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Time taken to execute the code")

class CodeExecutionWithVariablesResponse(BaseModel):
    result: Optional[Any] = Field(None, description="Execution result")
    variables: dict = Field(default_factory=dict, description="Dictionary of variables created by the code")
    output: Optional[str] = Field(None, description="Captured stdout output")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Time taken to execute the code")

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

def get_code_whisperer(app_state = Depends(get_app_state)) -> CodeWhisperer:
    """Dependency to get CodeWhisperer instance"""
    if not hasattr(app_state, 'code_whisperer') or app_state.code_whisperer is None:
        # Load configuration
        config = app_state.config
        app_state.code_whisperer = CodeWhisperer(config)
    return app_state.code_whisperer

@router.post("/", response_model=CodeExecutionResponse)
async def execute_code(
    request: CodeExecutionRequest,
    code_whisperer: CodeWhisperer = Depends(get_code_whisperer)
):
    """
    Execute Python code

    This endpoint:
    - Executes code in the environment
    - Returns results or error messages
    """
    import time
    start_time = time.time()

    print(f"DEBUG: Received code: {request.code}")  # Debug print

    try:
        print("DEBUG: Starting code execution")  # Debug print
        # Execute the code
        result, error = code_whisperer.execute_with_timeout(request.code)
        print(f"DEBUG: Execution result - Result: {result}, Error: {error}")  # Debug print

        execution_time = time.time() - start_time

        return CodeExecutionResponse(
            result=result,
            output=None,  # Output is captured internally by CodeWhisperer
            error=error,
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"DEBUG: Exception in endpoint: {e}")  # Debug print
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/with-variables", response_model=CodeExecutionWithVariablesResponse)
async def execute_code_with_variables(
    request: CodeExecutionRequest,
    code_whisperer: CodeWhisperer = Depends(get_code_whisperer)
):
    """
    Execute Python code and return created variables

    This endpoint:
    - Executes the code in the environment
    - Extracts and returns the variables created by the code
    - Returns results, variables, or error messages
    """
    import time
    start_time = time.time()

    try:
        # Execute the code and extract variables
        result, variables, error = code_whisperer.execute_with_variables(request.code)

        execution_time = time.time() - start_time

        return CodeExecutionWithVariablesResponse(
            result=result,
            variables=variables,
            output=None,  # Output is captured internally by CodeWhisperer
            error=error,
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )