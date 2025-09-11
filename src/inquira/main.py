from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import importlib.resources
import webbrowser
import threading
import time
import os
import uvicorn
from datetime import datetime
from .api.generate_schema import router as schema_router
from .api.chat import router as chat_router
from .api.auth import router as auth_router
from .api.settings import router as settings_router
from .api.data_preview import router as data_preview_router
from .api.code_execution import router as code_execution_router
from .api.api_key import router as api_key_router
from .config_models import AppConfig
from .websocket_manager import websocket_manager
from .database_manager import DatabaseManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the application"""
    print("API server started. Authentication system initialized.")

    # Initialize app state with None values
    app.state.api_key = None
    app.state.data_path = None
    app.state.schema_path = None
    app.state.context = None
    app.state.llm_service = None
    app.state.llm_initialized = False

    # Load merged configuration
    try:
        default_config_path = os.path.join(os.path.dirname(__file__), "app_config.json")
        app.state.config = AppConfig.load_merged_config(default_config_path)
        print("Configuration loaded successfully")
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        # Create a default config if loading fails
        app.state.config = AppConfig()

    # Initialize database manager
    app.state.db_manager = DatabaseManager(app.state.config)
    print("Database manager initialized")

    yield

    # Cleanup on shutdown
    print("Shutting down API server")
    if hasattr(app.state, 'db_manager'):
        app.state.db_manager.shutdown()

app = FastAPI(
    title="Inquira",
    version="1.0.0",
    lifespan=lifespan
)

def get_ui_dir() -> str:
    """
    Locate the UI directory for StaticFiles.

    Logic
    --------------
    Prefer the packaged UI shipped inside the wheel (``inquira/ui``). If not
    present (e.g., running from the repo before building the wheel), fall back
    to the local dev output at ``frontend/dist``.

    :returns: Absolute path to a directory that FastAPI/Starlette can serve.
    :rtype: str
    """
    # --- variables at the top (per your standard) ---
    packaged_ui = importlib.resources.files("inquira").joinpath("frontend", "dist")  # Traversable, not necessarily a Path
    dev_ui = "/Users/adarshmaurya/Downloads/Projects/inquira-ui/dist"
    print(f"Packaged UI path: {packaged_ui}")
    print(f"Dev UI path: {dev_ui}")

    # Prefer dev UI for debugging
    print(f"Checking dev UI: {dev_ui}")
    if os.path.exists(dev_ui):
        print(f"Using dev UI: {dev_ui}")
        return dev_ui

    # Fallback to packaged UI
    if packaged_ui.is_dir():
        print(f"Got the UI from wheel: {packaged_ui}")
        return str(packaged_ui)

    print(f"No UI found, using dev UI path: {dev_ui}")
    return dev_ui

app.mount("/ui", StaticFiles(directory=get_ui_dir(), html=True), name="ui")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vue dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:3000",  # Alternative dev port
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["set-cookie"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(api_key_router)
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(data_preview_router)
app.include_router(schema_router)
app.include_router(code_execution_router)

# WebSocket endpoint for real-time processing updates
@app.websocket("/ws/settings/{user_id}")
async def settings_websocket(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time settings processing updates"""
    print(f"🔌 [WebSocket] New WebSocket connection request for user: {user_id}")
    print(f"🔍 [WebSocket] User ID type: {type(user_id)}, value: '{user_id}'")

    # Check for common issues
    if user_id == "current_user":
        print(f"⚠️ [WebSocket] WARNING: Frontend is using 'current_user' instead of actual user ID!")
        print(f"💡 [WebSocket] Frontend should connect to: ws://localhost:8000/ws/settings/{user_id}")
        print(f"💡 [WebSocket] But it's connecting to: ws://localhost:8000/ws/settings/current_user")
        print(f"✅ [WebSocket] Accepting connection with 'current_user' for compatibility")

    await websocket_manager.connect(user_id, websocket)
    print(f"✅ [WebSocket] Connection established for user: {user_id}")
    print(f"🔍 [WebSocket] Active connections after connect: {list(websocket_manager.active_connections.keys())}")

    # Check for existing preview cache and create if missing
    try:
        from .database import get_user_settings
        from .api.data_preview import get_cached_preview, set_cached_preview, read_file_with_duckdb_sample, SampleType

        # Get user's data path
        user_settings = get_user_settings(user_id) or {}
        data_path = user_settings.get("data_path")

        if data_path:
            # Check cache status for all sample types and create cache if missing
            cache_status = {}
            for sample_type in [SampleType.random, SampleType.first]:
                cached_data = get_cached_preview(app.state, user_id, sample_type.value, data_path)

                if cached_data:
                    cache_status[sample_type.value] = "cached"
                    print(f"✅ [WebSocket] Cache found for {user_id}:{sample_type.value}")
                else:
                    # Cache doesn't exist, create it asynchronously
                    print(f"🔄 [WebSocket] Creating cache for {user_id}:{sample_type.value}")
                    try:
                        sample_data = read_file_with_duckdb_sample(data_path, sample_type.value, 100)
                        response_data = {
                            "success": True,
                            "data": sample_data,
                            "row_count": len(sample_data),
                            "file_path": data_path,
                            "sample_type": sample_type.value,
                            "message": f"Successfully loaded {len(sample_data)} {sample_type.value} sample rows"
                        }
                        set_cached_preview(app.state, user_id, sample_type.value, data_path, response_data)
                        cache_status[sample_type.value] = "cached"
                        print(f"✅ [WebSocket] Cache created for {user_id}:{sample_type.value} ({len(sample_data)} rows)")
                    except Exception as cache_error:
                        print(f"❌ [WebSocket] Failed to create cache for {user_id}:{sample_type.value}: {str(cache_error)}")
                        cache_status[sample_type.value] = "error"

            # Send cache status to client
            await websocket_manager.send_to_user(user_id, {
                "type": "cache_status",
                "data_path": data_path,
                "cache_status": cache_status,
                "message": f"Cache status checked for {data_path}",
                "timestamp": datetime.now().isoformat()
            })

            print(f"📊 [WebSocket] Cache status sent to user {user_id}: {cache_status}")

    except Exception as e:
        print(f"⚠️ [WebSocket] Error checking cache status: {str(e)}")

    try:
        while True:
            # Keep connection alive and handle any incoming messages
            print(f"👂 [WebSocket] Waiting for messages from user {user_id}...")
            data = await websocket.receive_text()
            print(f"📨 [WebSocket] Received message from user {user_id}: {data}")
            # For now, we just keep the connection alive
            # In the future, this could handle cancellation requests, etc.
    except Exception as e:
        print(f"❌ [WebSocket] Error for user {user_id}: {e}")
    finally:
        print(f"🔌 [WebSocket] Cleaning up connection for user {user_id}")
        await websocket_manager.disconnect(user_id)


@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint to check if API is running
    """
    return {"message": "Inquira is running", "version": "1.0.0"}


def run():
    HOST = "localhost"
    PORT = 8000
    UI = "/ui"
    # Open browser in a separate thread
    def open_browser():
        time.sleep(2)  # Wait for server to start
        webbrowser.open(f"http://{HOST}:{PORT}{UI}")

    threading.Thread(target=open_browser, daemon=True).start()

    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False
    )

if __name__ == "__main__":
    run()
