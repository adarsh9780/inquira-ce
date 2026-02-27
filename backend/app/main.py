import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

# Monkey patch aiosqlite.Connection to add is_alive method
# required by langgraph-checkpoint-sqlite v3.0.1+
if not hasattr(aiosqlite.Connection, "is_alive"):

    def is_alive(self):
        return True

    aiosqlite.Connection.is_alive = is_alive


from .v1.api.router import router as v1_router
from .v1.db.init import init_v1_database
from .v1.services.langgraph_workspace_manager import WorkspaceLangGraphManager
from .v1.services.workspace_deletion_service import WorkspaceDeletionService
from .core.config_models import AppConfig
from .core.logger import logprint, patch_print
from .services.code_executor import (
    prune_idle_workspace_kernels,
    shutdown_workspace_kernel_manager,
)
from .services.session_variable_store import session_variable_store
from .services.websocket_manager import websocket_manager
from .services.tracing import init_phoenix_tracing

APP_VERSION = "0.5.7a5"


def _default_cors_origins() -> list[str]:
    return [
        "http://localhost:5173",  # Vue dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:3000",  # Alternative dev port
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://tauri.localhost",  # Tauri webview
        "tauri://localhost",  # Tauri webview (custom protocol)
    ]


def _load_cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "").strip()
    if not configured:
        return _default_cors_origins()

    # Accept either comma-separated values or a JSON array.
    if configured.startswith("["):
        try:
            import json

            values = json.loads(configured)
        except Exception:
            values = []
    else:
        values = configured.split(",")

    parsed = [str(origin).strip() for origin in values if str(origin).strip()]
    return parsed or _default_cors_origins()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the application"""
    logprint("API server started. Authentication system initialized.")
    init_phoenix_tracing()

    # Initialize app state with None values
    app.state.api_key = None
    app.state.data_path = None
    app.state.schema_path = None
    app.state.context = None
    app.state.llm_service = None
    app.state.llm_initialized = False
    app.state.workspace_langgraph_manager = WorkspaceLangGraphManager()
    app.state.workspace_deletion_service = WorkspaceDeletionService()

    # Initialize LangGraph Agent with Persistence
    try:
        from .agent.graph import build_graph

        # Use dedicated chat_history.db in the user's home directory
        db_path = Path.home() / ".inquira" / "chat_history.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # We need to store the checkpointer itself to close it later,
        # or we rely on the fact that build_graph uses it.
        # However, AsyncSqliteSaver is an async context manager.
        # We need to enter it to get the usable checkpointer.

        # AsyncSqliteSaver.from_conn_string returns an async context manager.
        # We must assign the context manager to a variable, then await __aenter__()
        # to get the *actual* checkpointer instance.

        checkpointer_cm = AsyncSqliteSaver.from_conn_string(str(db_path))
        checkpointer = await checkpointer_cm.__aenter__()

        # Store context manager for cleanup, and checkpointer for reference (if needed)
        app.state.checkpointer_cm = checkpointer_cm

        app.state.agent_graph = build_graph(checkpointer=checkpointer)
        logprint(f"LangGraph agent initialized with persistence at: {db_path}")
    except Exception as e:
        logprint(f"Failed to initialize LangGraph agent: {e}", level="error")
        app.state.agent_graph = None
        app.state.checkpointer_cm = None

    # Load merged configuration
    try:
        default_config_path = os.path.join(os.path.dirname(__file__), "app_config.json")
        app.state.config = AppConfig.load_merged_config(default_config_path)
        logprint("Configuration loaded successfully")
    except Exception as e:
        logprint(f"Failed to load configuration: {e}", level="error")
        # Create a default config if loading fails
        app.state.config = AppConfig()

    # Initialize v1 ORM database schema
    try:
        await init_v1_database()
        logprint("API v1 ORM schema initialized")
    except Exception as e:
        logprint(f"Failed to initialize API v1 ORM schema: {e}", level="error")
        raise

    # Start session cleanup task
    cleanup_task = asyncio.create_task(session_cleanup_worker())
    logprint("Session cleanup worker started")

    yield

    # Cleanup on shutdown
    logprint("Shutting down API server")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    if hasattr(app.state, "workspace_langgraph_manager") and app.state.workspace_langgraph_manager:
        try:
            await app.state.workspace_langgraph_manager.shutdown()
        except Exception as e:
            logprint(f"Error closing workspace LangGraph manager: {e}", level="error")

    if hasattr(app.state, "workspace_deletion_service") and app.state.workspace_deletion_service:
        try:
            await app.state.workspace_deletion_service.shutdown()
        except Exception as e:
            logprint(f"Error closing workspace deletion service: {e}", level="error")

    if hasattr(app.state, "checkpointer_cm") and app.state.checkpointer_cm:
        logprint("Closing LangGraph checkpointer connection...")
        try:
            await app.state.checkpointer_cm.__aexit__(None, None, None)
        except Exception as e:
            logprint(f"Error closing checkpointer: {e}", level="error")

    try:
        await shutdown_workspace_kernel_manager()
    except Exception as e:
        logprint(f"Error shutting down workspace kernels: {e}", level="error")


async def session_cleanup_worker():
    """Background task to clean up expired sessions"""
    while True:
        try:
            session_variable_store.cleanup_expired_sessions()
            await prune_idle_workspace_kernels()
            await asyncio.sleep(300)  # Clean up every 5 minutes
        except Exception as e:
            logprint(f"Error in session cleanup: {e}", level="error")
            await asyncio.sleep(60)  # Wait a minute before retrying


app = FastAPI(title="Inquira", version="1.0.0", lifespan=lifespan)

# Route legacy print() to structured logger
patch_print()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    
    # Log the full traceback using logprint so we can see it in terminal
    logprint(f"Unhandled server error at {request.url}: {exc}", level="error")
    for line in traceback.format_exc().splitlines():
        logprint(line, level="error")
        
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    # Keep local-dev origins resilient across Vite/Tauri port changes.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://tauri\.localhost$|^tauri://localhost$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

# Include v1 router only
app.include_router(v1_router)


# WebSocket endpoint for real-time processing updates
@app.websocket("/ws/settings/{user_id}")
async def settings_websocket(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time settings processing updates"""
    logprint(f"🔌 [WebSocket] New WebSocket connection request for user: {user_id}")
    logprint(f"🔍 [WebSocket] User ID type: {type(user_id)}, value: '{user_id}'")

    # Check for common issues
    if user_id == "current_user":
        logprint(
            "⚠️ [WebSocket] WARNING: Frontend is using 'current_user' instead of actual user ID!"
        )
        logprint(
            f"💡 [WebSocket] Frontend should connect to: ws://localhost:8000/ws/settings/{user_id}"
        )
        logprint(
            "💡 [WebSocket] But it's connecting to: ws://localhost:8000/ws/settings/current_user"
        )
        logprint(
            "✅ [WebSocket] Accepting connection with 'current_user' for compatibility"
        )

    await websocket_manager.connect(user_id, websocket)
    logprint(f"✅ [WebSocket] Connection established for user: {user_id}")
    logprint(
        f"🔍 [WebSocket] Active connections after connect: {list(websocket_manager.active_connections.keys())}"
    )

    # V1 runtime keeps workspace-scoped state; legacy cache bootstrap is disabled.

    try:
        while True:
            # Keep connection alive and handle any incoming messages
            logprint(f"👂 [WebSocket] Waiting for messages from user {user_id}...")
            data = await websocket.receive_text()
            logprint(f"📨 [WebSocket] Received message from user {user_id}: {data}")
            # For now, we just keep the connection alive
            # In the future, this could handle cancellation requests, etc.
    except Exception as e:
        logprint(f"❌ [WebSocket] Error for user {user_id}: {e}", level="error")
    finally:
        logprint(f"🔌 [WebSocket] Cleaning up connection for user {user_id}")
        await websocket_manager.disconnect(user_id)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """No favicon endpoint while static files are disabled."""
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint to check if API is running
    """
    return {"message": "Inquira is running", "version": APP_VERSION}


def run(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="inquira",
        description="Run the Inquira API and bundled UI",
    )
    parser.add_argument(
        "--no-file-dialog",
        dest="allow_file_dialog",
        action="store_false",
        help="Disable the native file picker endpoint",
    )
    parser.add_argument(
        "--allow-file-dialog",
        dest="allow_file_dialog",
        action="store_true",
        help="Explicitly enable the native file picker (overrides environment)",
    )
    args = parser.parse_args(argv)

    env_flag = os.getenv("INQUIRA_ALLOW_FILE_DIALOG")
    if args.allow_file_dialog is not None:
        allow_file_dialog = args.allow_file_dialog
    elif env_flag is not None:
        allow_file_dialog = env_flag not in {"0", "false", "False"}
    else:
        allow_file_dialog = True  # default to enabled

    app.state.allow_file_dialog = allow_file_dialog

    HOST = "localhost"
    PORT = 8000

    logprint(f"Launching Inquira backend (v{APP_VERSION})")
    access_log = True
    uvicorn_log_level = "info"
    try:
        default_config_path = os.path.join(os.path.dirname(__file__), "app_config.json")
        cfg = AppConfig.load_merged_config(default_config_path)
        access_log = bool(cfg.LOGGING.uvicorn_access_log)
        uvicorn_log_level = str(cfg.LOGGING.uvicorn_log_level or "info").lower()
    except Exception:
        access_log = True
        uvicorn_log_level = "info"

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False,
        access_log=access_log,
        log_level=uvicorn_log_level,
    )


if __name__ == "__main__":
    run()
