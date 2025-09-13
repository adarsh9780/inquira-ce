from fastapi import APIRouter, HTTPException, Request, Depends
from ..logger import logprint
from pydantic import BaseModel, Field
from typing import Any, Optional, Dict

from ..code_whisperer import CodeWhisperer
from ..session_variable_store import session_variable_store
from .auth import get_current_user

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

    # Inject database connections if available
    if hasattr(app_state, 'db_manager') and hasattr(app_state, 'data_path'):
        # Get the current user's database connection
        # Note: We need to get user_id from the request context
        # This will be handled in the endpoint where we have access to current_user
        pass

    return app_state.code_whisperer

@router.post("/", response_model=CodeExecutionResponse)
async def execute_code(
    request: CodeExecutionRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """
    Execute Python code

    This endpoint:
    - Executes code in the environment
    - Returns results or error messages
    """
    import time
    start_time = time.time()

    logprint(f"DEBUG: Received code: {request.code}", level="debug")

    try:
        logprint("DEBUG: Starting code execution", level="debug")

        # Get CodeWhisperer instance
        code_whisperer = get_code_whisperer(app_state)

        # Inject database connection if available
        if (hasattr(app_state, 'db_manager') and
            hasattr(app_state, 'data_path') and
            app_state.data_path):
            try:
                user_id = current_user["user_id"]
                db_connection = app_state.db_manager.get_connection(user_id, app_state.data_path)
                # Inject the connection into CodeWhisperer as 'conn'
                code_whisperer.set_cached_connection("conn", db_connection)
                logprint(f"DEBUG: Injected database connection as 'conn' for user {user_id}", level="debug")
            except Exception as e:
                logprint(f"DEBUG: Could not inject database connection: {e}", level="debug")

        # Execute the code with user session
        result, error = code_whisperer.execute_with_timeout(request.code, current_user["user_id"])
        logprint(f"DEBUG: Execution result - Result: {result}, Error: {error}", level="debug")

        execution_time = time.time() - start_time

        return CodeExecutionResponse(
            result=result,
            output=None,  # Output is captured internally by CodeWhisperer
            error=error,
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logprint(f"DEBUG: Exception in endpoint: {e}", level="debug")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/session-variables", response_model=Dict[str, Any])
async def get_session_variables(current_user: dict = Depends(get_current_user)):
    """
    Get current session variables for debugging purposes

    Returns:
        Dictionary containing global and local variables in the user's session
    """
    try:
        global_vars = session_variable_store.get_global_vars(current_user["user_id"])
        local_vars = session_variable_store.get_local_vars(current_user["user_id"])

        # Filter out builtins for cleaner output
        filtered_globals = {k: v for k, v in global_vars.items() if k != '__builtins__'}
        filtered_locals = {k: v for k, v in local_vars.items() if k != '__builtins__'}

        return {
            "user_id": current_user["user_id"],
            "global_variables": filtered_globals,
            "local_variables": filtered_locals,
            "global_count": len(filtered_globals),
            "local_count": len(filtered_locals)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session variables: {str(e)}"
        )


@router.delete("/session-variables")
async def clear_session_variables(current_user: dict = Depends(get_current_user)):
    """
    Clear all session variables for the current user
    """
    try:
        session_variable_store.clear_session(current_user["user_id"])
        return {"message": f"Session variables cleared for user {current_user['user_id']}"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear session variables: {str(e)}"
        )


@router.post("/with-variables", response_model=CodeExecutionWithVariablesResponse)
async def execute_code_with_variables(
    request: CodeExecutionRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
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
        # Get CodeWhisperer instance
        code_whisperer = get_code_whisperer(app_state)

        # Inject database connection if available
        if (hasattr(app_state, 'db_manager') and
            hasattr(app_state, 'data_path') and
            app_state.data_path):
            try:
                user_id = current_user["user_id"]
                db_connection = app_state.db_manager.get_connection(user_id, app_state.data_path)
                # Inject the connection into CodeWhisperer as 'conn'
                code_whisperer.set_cached_connection("conn", db_connection)
                logprint(f"DEBUG: Injected database connection as 'conn' for user {user_id}", level="debug")
            except Exception as e:
                logprint(f"DEBUG: Could not inject database connection: {e}", level="debug")

        # Execute the code and extract variables with user session
        result, variables, error = code_whisperer.execute_with_variables(request.code, current_user["user_id"])

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
