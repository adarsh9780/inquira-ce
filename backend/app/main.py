import argparse
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

# Monkey patch aiosqlite.Connection to add is_alive method
# required by langgraph-checkpoint-sqlite v3.0.1+
if not hasattr(aiosqlite.Connection, "is_alive"):

    def is_alive(self):
        return True

    aiosqlite.Connection.is_alive = is_alive


from .api.api_test import router as api_test_router
from .api.auth import router as auth_router
from .api.chat import router as chat_router
from .api.data_preview import router as data_preview_router
from .api.datasets import router as datasets_router
from .api.schemas import router as schema_router
from .api.legal import router as legal_router
from .api.settings import router as settings_router
from .api.system import router as system_router
from .core.config_models import AppConfig
from .database.database_manager import DatabaseManager
from .core.logger import logprint, patch_print
from .services.session_variable_store import session_variable_store
from .services.websocket_manager import websocket_manager

APP_VERSION = "0.4.6a0"


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

    # Initialize database manager
    app.state.db_manager = DatabaseManager(app.state.config)
    logprint("Database manager initialized")

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

    if hasattr(app.state, "db_manager"):
        app.state.db_manager.shutdown()

    if hasattr(app.state, "checkpointer_cm") and app.state.checkpointer_cm:
        logprint("Closing LangGraph checkpointer connection...")
        try:
            await app.state.checkpointer_cm.__aexit__(None, None, None)
        except Exception as e:
            logprint(f"Error closing checkpointer: {e}", level="error")


async def session_cleanup_worker():
    """Background task to clean up expired sessions"""
    while True:
        try:
            session_variable_store.cleanup_expired_sessions()
            await asyncio.sleep(300)  # Clean up every 5 minutes
        except Exception as e:
            logprint(f"Error in session cleanup: {e}", level="error")
            await asyncio.sleep(60)  # Wait a minute before retrying


app = FastAPI(title="Inquira", version="1.0.0", lifespan=lifespan)

# Route legacy print() to structured logger
patch_print()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vue dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:3000",  # Alternative dev port
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

# Include all routers
app.include_router(auth_router)

app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(data_preview_router)
app.include_router(schema_router)
app.include_router(api_test_router)
app.include_router(datasets_router)
app.include_router(system_router)
app.include_router(legal_router)


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

    # Check for existing preview cache and create if missing
    try:
        from .api.data_preview import (
            SampleType,
            get_cached_preview,
            read_file_with_duckdb_sample,
            set_cached_preview,
        )
        from .database.database import get_user_settings

        # Get user's data path
        user_settings = get_user_settings(user_id) or {}
        data_path = user_settings.get("data_path")

        if data_path:
            if isinstance(data_path, str) and data_path.startswith("browser://"):
                # Browser-native datasets are previewed client-side.
                await websocket_manager.send_to_user(
                    user_id,
                    {
                        "type": "cache_status",
                        "data_path": data_path,
                        "cache_status": {
                            SampleType.random.value: "skipped",
                            SampleType.first.value: "skipped",
                        },
                        "message": "Preview cache skipped for browser-native dataset (handled in frontend runtime).",
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                return

            # Check cache status for all sample types and create cache if missing
            cache_status = {}
            for sample_type in [SampleType.random, SampleType.first]:
                cached_data = get_cached_preview(
                    app.state, user_id, sample_type.value, data_path
                )

                if cached_data:
                    cache_status[sample_type.value] = "cached"
                    logprint(
                        f"✅ [WebSocket] Cache found for {user_id}:{sample_type.value}"
                    )
                else:
                    # Cache doesn't exist, create it asynchronously
                    logprint(
                        f"🔄 [WebSocket] Creating cache for {user_id}:{sample_type.value}"
                    )
                    try:
                        sample_data = read_file_with_duckdb_sample(
                            data_path, sample_type.value, 100
                        )
                        response_data = {
                            "success": True,
                            "data": sample_data,
                            "row_count": len(sample_data),
                            "file_path": data_path,
                            "sample_type": sample_type.value,
                            "message": f"Successfully loaded {len(sample_data)} {sample_type.value} sample rows",
                        }
                        set_cached_preview(
                            app.state,
                            user_id,
                            sample_type.value,
                            data_path,
                            response_data,
                        )
                        cache_status[sample_type.value] = "cached"
                        logprint(
                            f"✅ [WebSocket] Cache created for {user_id}:{sample_type.value} ({len(sample_data)} rows)"
                        )
                    except Exception as cache_error:
                        logprint(
                            f"❌ [WebSocket] Failed to create cache for {user_id}:{sample_type.value}: {str(cache_error)}",
                            level="error",
                        )
                        cache_status[sample_type.value] = "error"

            # Send cache status to client
            await websocket_manager.send_to_user(
                user_id,
                {
                    "type": "cache_status",
                    "data_path": data_path,
                    "cache_status": cache_status,
                    "message": f"Cache status checked for {data_path}",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logprint(
                f"📊 [WebSocket] Cache status sent to user {user_id}: {cache_status}"
            )

    except Exception as e:
        logprint(f"⚠️ [WebSocket] Error checking cache status: {str(e)}", level="error")

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
    access_log = False
    uvicorn_log_level = "error"
    try:
        default_config_path = os.path.join(os.path.dirname(__file__), "app_config.json")
        cfg = AppConfig.load_merged_config(default_config_path)
        access_log = bool(cfg.LOGGING.uvicorn_access_log)
        uvicorn_log_level = str(cfg.LOGGING.uvicorn_log_level or "error").lower()
    except Exception:
        access_log = False
        uvicorn_log_level = "error"

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
