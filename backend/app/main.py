import argparse
import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite

# Monkey patch aiosqlite.Connection to add is_alive method
# required by langgraph-checkpoint-sqlite v3.0.1+
if not hasattr(aiosqlite.Connection, "is_alive"):

    def is_alive(self):
        return True

    aiosqlite.Connection.is_alive = is_alive


from .v1.api.router import router as v1_router
from .v1.db.session import AppDataSessionLocal
from .v1.repositories.workspace_repository import WorkspaceRepository

from .v1.db.init import init_v1_database
from .v1.services.langgraph_workspace_manager import WorkspaceLangGraphManager
from .v1.services.workspace_deletion_service import WorkspaceDeletionService
from .v1.services.dataset_deletion_service import DatasetDeletionService
from .v1.services.dataset_ingestion_service import DatasetIngestionService
from .core.config_models import AppConfig
from .core.logger import logprint, patch_print
from .services.code_executor import (
    get_workspace_kernel_status,
    prune_idle_workspace_kernels,
    shutdown_workspace_kernel_manager,
)
from .services.artifact_scratchpad import get_artifact_scratchpad_store
from .services.execution_config import load_execution_runtime_config
from .services.terminal_executor import shutdown_terminal_sessions
from .services.session_variable_store import session_variable_store
from .services.websocket_manager import websocket_manager
from .services.tracing import init_phoenix_tracing

APP_VERSION = "0.5.33"
_LOG_LEVELS = {"trace", "debug", "info", "warning", "error", "critical"}


def _resolve_runtime_host(default: str = "localhost") -> str:
    return str(os.getenv("INQUIRA_HOST") or default).strip() or default


def _resolve_runtime_port(default: int = 8000) -> int:
    raw_value = str(os.getenv("INQUIRA_PORT") or "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _default_cors_origins() -> list[str]:
    return [
        "http://localhost:5173",  # Vue dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:3000",  # Alternative dev port
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://tauri.localhost",  # Tauri webview in packaged desktop runs
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

    # Initialize app state with None values
    app.state.api_key = None
    app.state.data_path = None
    app.state.schema_path = None
    app.state.context = None
    app.state.llm_service = None
    app.state.llm_initialized = False
    app.state.workspace_langgraph_manager = WorkspaceLangGraphManager()
    app.state.workspace_deletion_service = WorkspaceDeletionService()
    app.state.dataset_deletion_service = DatasetDeletionService()
    app.state.dataset_ingestion_service = DatasetIngestionService()

    # Load merged configuration
    try:
        default_config_path = os.path.join(os.path.dirname(__file__), "app_config.json")
        app.state.config = AppConfig.load_merged_config(default_config_path)
        logprint("Configuration loaded successfully")
    except Exception as e:
        logprint(f"Failed to load configuration: {e}", level="error")
        # Create a default config if loading fails
        app.state.config = AppConfig()

    # Initialize tracing early so startup/request spans are captured.
    init_phoenix_tracing()

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

    if hasattr(app.state, "dataset_deletion_service") and app.state.dataset_deletion_service:
        try:
            await app.state.dataset_deletion_service.shutdown()
        except Exception as e:
            logprint(f"Error closing dataset deletion service: {e}", level="error")

    if hasattr(app.state, "dataset_ingestion_service") and app.state.dataset_ingestion_service:
        try:
            await app.state.dataset_ingestion_service.shutdown()
        except Exception as e:
            logprint(f"Error closing dataset ingestion service: {e}", level="error")

    try:
        await shutdown_workspace_kernel_manager()
    except Exception as e:
        logprint(f"Error shutting down workspace kernels: {e}", level="error")
    try:
        await shutdown_terminal_sessions()
    except Exception as e:
        logprint(f"Error shutting down terminal sessions: {e}", level="error")


async def session_cleanup_worker():
    """Background task to clean up expired sessions"""
    while True:
        try:
            session_variable_store.cleanup_expired_sessions()
            await prune_idle_workspace_kernels()
            runtime_cfg = load_execution_runtime_config()
            # Scratchpad retention enforcement for manifest-backed artifacts.
            _ = runtime_cfg  # reserved for future per-config tunables
            get_artifact_scratchpad_store().prune_all()
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

    request_id = uuid.uuid4().hex[:12]
    # Log the full traceback using logprint so we can see it in terminal
    logprint(
        f"Unhandled server error at {request.url} (request_id={request_id}): {exc}",
        level="error",
    )
    for line in traceback.format_exc().splitlines():
        logprint(line, level="error")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "message": "Something went wrong while processing your request. Please retry.",
            "request_id": request_id,
        },
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_load_cors_origins(),
    # Keep local-dev origins resilient across Vite/Tauri port changes.
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        r"|^https?://tauri\.localhost(:\d+)?$"
        r"|^tauri://localhost$"
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

# Include v1 router only
app.include_router(v1_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend"}



async def _cancel_task(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _stream_kernel_status_updates(user_id: str, workspace_id: str) -> None:
    last_status: str | None = None
    while True:
        status_value = await get_workspace_kernel_status(workspace_id)
        if status_value != last_status:
            await websocket_manager.send_to_user(
                user_id,
                {
                    "type": "kernel_status",
                    "workspace_id": workspace_id,
                    "status": status_value,
                },
            )
            last_status = status_value
        await asyncio.sleep(1)


@app.websocket("/ws/settings/{user_id}")
async def settings_websocket(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time settings processing updates"""
    logprint(f"🔌 [WebSocket] New WebSocket connection request for path user: {user_id}")

    # CE mode: accept all connections as local-user
    auth_user_id = "local-user"

    await websocket_manager.connect(auth_user_id, websocket)
    logprint(f"✅ [WebSocket] Connection established for user: {auth_user_id}")
    logprint(
        f"🔍 [WebSocket] Active connections after connect: {list(websocket_manager.active_connections.keys())}"
    )

    kernel_status_task: asyncio.Task | None = None
    try:
        while True:
            logprint(f"👂 [WebSocket] Waiting for messages from user {auth_user_id}...")
            data = await websocket.receive_text()
            logprint(f"📨 [WebSocket] Received message from user {auth_user_id}: {data}")
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            message_type = str(message.get("type") or "").strip().lower()
            if message_type != "subscribe_kernel_status":
                continue

            workspace_id = str(message.get("workspace_id") or "").strip()
            await _cancel_task(kernel_status_task)
            kernel_status_task = None

            if not workspace_id:
                continue

            kernel_status_task = asyncio.create_task(
                _stream_kernel_status_updates(auth_user_id, workspace_id)
            )
    except Exception as e:
        logprint(f"❌ [WebSocket] Error for user {auth_user_id}: {e}", level="error")
    finally:
        await _cancel_task(kernel_status_task)
        logprint(f"🔌 [WebSocket] Cleaning up connection for user {auth_user_id}")
        await websocket_manager.disconnect(auth_user_id)


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

    HOST = _resolve_runtime_host()
    PORT = _resolve_runtime_port()

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

    override_level = str(os.getenv("INQUIRA_LOG_CONSOLE_LEVEL") or "").strip().lower()
    if override_level in _LOG_LEVELS:
        uvicorn_log_level = override_level
        if override_level in {"error", "critical"}:
            access_log = False

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
