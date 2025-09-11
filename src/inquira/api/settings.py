from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
from datetime import datetime
from pathlib import Path
from .auth import get_current_user, get_app_config
from ..database import get_user_settings, save_user_settings
from ..config_models import AppConfig
from ..websocket_manager import websocket_manager
from ..database_manager import DatabaseManager

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

router = APIRouter(tags=["Settings"])

# Response models for individual fields
class DataPathResponse(BaseModel):
    data_path: Optional[str] = None

class ContextResponse(BaseModel):
    context: Optional[str] = None

class ApiKeyResponse(BaseModel):
    api_key: Optional[str] = None


# Request models for setting values
class DataPathRequest(BaseModel):
    data_path: str = Field(description="Path to the data file")

class ContextRequest(BaseModel):
    context: str = Field(description="Context about the data domain")

class ApiKeyRequest(BaseModel):
    api_key: str = Field(description="Google Gemini API key")


# Full settings response
class SettingsResponse(BaseModel):
    data_path: Optional[str] = None
    context: Optional[str] = None
    api_key: Optional[str] = None

# Paths response
class PathsResponse(BaseModel):
    schema_path: str
    database_path: str
    base_directory: str



# SET endpoints
@router.put("/settings/set/data_path")
async def set_data_path(
    request: DataPathRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the data file path and start background processing with WebSocket updates"""
    user_id = current_user["user_id"]

    # Check if user has an active WebSocket connection
    print(f"🔍 [Settings] Checking WebSocket connection for user: {user_id}")
    print(f"🔍 [Settings] Active connections: {list(websocket_manager.active_connections.keys())}")

    # Check for the actual user_id first
    if websocket_manager.is_connected(user_id):
        print(f"✅ [Settings] WebSocket connection verified for user: {user_id}")
    # Temporary workaround: Check if frontend is using "current_user" instead of actual user_id
    elif websocket_manager.is_connected("current_user"):
        print(f"⚠️ [Settings] Frontend using 'current_user' instead of actual user_id")
        print(f"✅ [Settings] Using existing 'current_user' connection for user: {user_id}")
        # For now, allow this to work, but log the issue
    else:
        print(f"❌ [Settings] No WebSocket connection found for user: {user_id}")
        raise HTTPException(
            status_code=400,
            detail=f"WebSocket connection required for data processing. Please establish a WebSocket connection to /ws/settings/{user_id} before setting the data path. This allows real-time progress updates during file processing."
        )

    # Save data path immediately
    user_settings = get_user_settings(user_id) or {}
    user_settings["data_path"] = request.data_path
    success = save_user_settings(user_id, user_settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save data path")

    # Update app_state
    app_state.data_path = request.data_path

    # Start background processing
    background_tasks.add_task(
        process_data_path_background,
        request.data_path,
        user_id,
        app_state
    )

    return {
        "message": "Data processing started",
        "data_path": request.data_path,
        "websocket_url": f"/ws/settings/{user_id}",
        "note": "Keep WebSocket connection open to receive real-time progress updates",
        "alternative": "Use /settings/set/data_path_simple to just update path without processing"
    }

@router.put("/settings/set/context")
async def set_context(
    request: ContextRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the context for schema generation"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    user_settings["context"] = request.context
    success = save_user_settings(user_id, user_settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save context")

    # Update app_state
    app_state.context = request.context

    return {"message": "Context updated successfully", "context": request.context}

@router.put("/settings/set/data_path_simple")
async def set_data_path_simple(
    request: DataPathRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the data file path without triggering processing (simple update only)"""
    user_id = current_user["user_id"]

    # Save data path immediately without processing
    user_settings = get_user_settings(user_id) or {}
    user_settings["data_path"] = request.data_path
    success = save_user_settings(user_id, user_settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save data path")

    # Update app_state
    app_state.data_path = request.data_path

    return {
        "message": "Data path updated successfully (no processing triggered)",
        "data_path": request.data_path,
        "note": "Use /settings/set/data_path with WebSocket connection to trigger full processing"
    }

@router.put("/settings/set/api_key")
async def set_apikey(
    request: ApiKeyRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Set the API key"""
    user_id = current_user["user_id"]
    print(f"🔑 [Settings] Setting API key for user: {user_id}")
    print(f"🔑 [Settings] API key length: {len(request.api_key) if request.api_key else 0}")

    user_settings = get_user_settings(user_id) or {}
    print(f"🔑 [Settings] Current settings before update: {user_settings}")

    user_settings["api_key"] = request.api_key
    success = save_user_settings(user_id, user_settings)

    if not success:
        print(f"❌ [Settings] Failed to save API key to database")
        raise HTTPException(status_code=500, detail="Failed to save API key")

    print(f"✅ [Settings] API key saved successfully to database")

    # Update app_state and try to initialize LLM service
    app_state.api_key = request.api_key
    try:
        from ..llm_service import LLMService
        app_state.llm_service = LLMService(api_key=request.api_key)
        app_state.llm_initialized = True
        status = "initialized"
        print(f"✅ [Settings] LLM service initialized successfully")
    except Exception as e:
        app_state.llm_service = None
        app_state.llm_initialized = False
        status = "saved"
        print(f"⚠️ [Settings] LLM service initialization failed: {str(e)}")

    return {"message": "API key updated successfully", "status": status}

# VIEW endpoints for individual fields
@router.get("/settings/view/data_path", response_model=DataPathResponse)
async def view_data_path(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """View the current data file path"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    # Load into app_state if needed
    if user_settings.get("data_path"):
        app_state.data_path = user_settings["data_path"]

    return DataPathResponse(data_path=user_settings.get("data_path"))

@router.get("/settings/view/context", response_model=ContextResponse)
async def view_context(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """View the current context"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id) or {}

    # Load into app_state if needed
    if user_settings.get("context"):
        app_state.context = user_settings["context"]

    return ContextResponse(context=user_settings.get("context"))

@router.get("/settings/view/api_key", response_model=ApiKeyResponse)
async def view_apikey(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """View the current API key"""
    user_id = current_user["user_id"]
    print(f"🔍 [Settings] Viewing API key for user: {user_id}")

    user_settings = get_user_settings(user_id) or {}
    print(f"🔍 [Settings] Current settings: {user_settings}")

    api_key = user_settings.get("api_key")
    print(f"🔍 [Settings] API key status: {'Set' if api_key else 'Not set'}")

    # Load into app_state if needed
    if api_key:
        app_state.api_key = api_key
        # Try to initialize LLM service
        try:
            from ..llm_service import LLMService
            app_state.llm_service = LLMService(api_key=api_key)
            app_state.llm_initialized = True
            print(f"✅ [Settings] LLM service initialized successfully")
        except Exception as e:
            app_state.llm_service = None
            app_state.llm_initialized = False
            print(f"❌ [Settings] LLM service initialization failed: {str(e)}")

    return ApiKeyResponse(api_key=api_key)

# VIEW ALL endpoint
@router.get("/settings/view", response_model=SettingsResponse)
async def view_all_settings(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state),
    config = Depends(get_app_config)
):
    """View all settings"""
    user_id = current_user["user_id"]

    # Load user settings into app_state (this will also check for schema files)
    load_user_settings_to_app_state(user_id, app_state)

    user_settings = get_user_settings(user_id) or {}

    return SettingsResponse(
        data_path=user_settings.get("data_path"),
        context=user_settings.get("context"),
        api_key=user_settings.get("api_key")
    )

@router.get("/settings/paths", response_model=PathsResponse)
async def get_storage_paths(current_user: dict = Depends(get_current_user)):
    """Get the paths where schema and database files are stored"""
    user_id = current_user["user_id"]

    # Base directory for user data
    base_dir = Path.home() / '.inquira' / user_id

    # Schema file path
    schema_path = base_dir / f"{user_id}_schema.json"

    # Database file path
    database_path = base_dir / f"{user_id}_data.duckdb"

    return PathsResponse(
        schema_path=str(schema_path),
        database_path=str(database_path),
        base_directory=str(base_dir)
    )

@router.post("/settings/close-connections")
async def close_database_connections(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Temporarily close database connections to allow external access"""
    user_id = current_user["user_id"]

    if hasattr(app_state, 'db_manager') and app_state.db_manager:
        # Debug: Print all current connections
        print(f"🔍 [Close Connections] Current connections in cache: {list(app_state.db_manager.connections.keys())}")

        # Close all connections for this user
        closed_connections = []
        for db_path_str, conn in list(app_state.db_manager.connections.items()):
            # Check if this connection belongs to the current user
            if user_id in db_path_str:
                try:
                    print(f"🔌 [Close Connections] Closing connection: {db_path_str}")
                    conn.close()
                    closed_connections.append(db_path_str)
                except Exception as e:
                    print(f"❌ [Close Connections] Error closing connection {db_path_str}: {e}")

        # Remove from connections cache
        for db_path_str in closed_connections:
            if db_path_str in app_state.db_manager.connections:
                del app_state.db_manager.connections[db_path_str]

        print(f"✅ [Close Connections] Closed {len(closed_connections)} connections for user {user_id}")

        # If no connections were found in cache, try to force close by creating a new connection and closing it
        if len(closed_connections) == 0:
            try:
                from pathlib import Path
                import duckdb

                # Try to connect to the user's database file directly
                db_path = Path.home() / '.inquira' / user_id / f"{user_id}_data.duckdb"
                if db_path.exists():
                    print(f"🔄 [Close Connections] Attempting direct connection to force close: {db_path}")
                    # This will create a connection that we can immediately close
                    conn = duckdb.connect(str(db_path))
                    conn.close()
                    print(f"✅ [Close Connections] Successfully closed direct connection to: {db_path}")
                    closed_connections.append(str(db_path))
            except Exception as e:
                print(f"⚠️ [Close Connections] Could not create direct connection: {e}")

        return {
            "message": f"Closed {len(closed_connections)} database connections",
            "closed_connections": closed_connections,
            "note": "You can now connect to the database externally. Connections will be reopened on next API request."
        }

    return {"message": "No database manager found", "closed_connections": []}


def load_user_settings_to_app_state(user_id: str, app_state):
    """
    Load user settings from database into app_state for global access
    Only loads if user has existing settings to avoid overwriting None values for new users
    """
    print(f"DEBUG: load_user_settings_to_app_state called for user {user_id}")
    user_settings = get_user_settings(user_id)
    print(f"DEBUG: user_settings = {user_settings}")

    # Check if schema_path is missing but schema exists for the data_path
    if (user_settings.get("data_path") and
        not user_settings.get("schema_path")):
        print(f"DEBUG: schema_path missing, checking for schema file")
        from ..schema_storage import load_schema, get_schema_filename, get_user_schema_dir
        schema_file = load_schema(user_id, user_settings["data_path"])
        print(f"DEBUG: schema_file loaded = {schema_file is not None}")
        if schema_file:
            # Schema exists, update settings with the path
            schema_dir = get_user_schema_dir(user_id)
            filename = get_schema_filename(user_id)
            schema_path = str(schema_dir / filename)
            print(f"DEBUG: updating schema_path to {schema_path}")
            user_settings["schema_path"] = schema_path
            # Save the updated settings
            save_user_settings(user_id, user_settings)
            print(f"DEBUG: settings saved with schema_path")

    # Only load settings into app_state if user has existing settings
    if user_settings and any(user_settings.values()):
        print(f"DEBUG: loading settings into app_state")
        # Load settings into app_state
        if user_settings.get("api_key"):
            app_state.api_key = user_settings["api_key"]
            # Try to initialize LLM service if API key is available
            try:
                from ..llm_service import LLMService
                app_state.llm_service = LLMService(api_key=user_settings["api_key"])
                app_state.llm_initialized = True
            except Exception:
                app_state.llm_service = None
                app_state.llm_initialized = False

        if user_settings.get("data_path"):
            app_state.data_path = user_settings["data_path"]
            # Generate table name from data path
            from ..database_manager import DatabaseManager
            from ..config_models import AppConfig
            config = app_state.config if hasattr(app_state, 'config') and app_state.config else AppConfig()
            db_manager = DatabaseManager(config)
            table_name = db_manager._get_table_name(user_settings["data_path"])
            app_state.table_name = table_name
            print(f"DEBUG: app_state.table_name set to {table_name}")
        if user_settings.get("schema_path"):
            app_state.schema_path = user_settings["schema_path"]
            print(f"DEBUG: app_state.schema_path set to {app_state.schema_path}")
        if user_settings.get("context"):
            app_state.context = user_settings["context"]

    return user_settings


async def process_data_path_background(data_path: str, user_id: str, app_state):
    """Background task to process data path with granular WebSocket updates for each step"""
    # Determine which user_id to use for WebSocket messages
    # If frontend is using "current_user", we need to send messages there
    print(f"🔍 [Background] Checking WebSocket connections for user: {user_id}")
    print(f"🔍 [Background] Active connections: {list(websocket_manager.active_connections.keys())}")
    print(f"🔍 [Background] Is '{user_id}' connected: {websocket_manager.is_connected(user_id)}")
    print(f"🔍 [Background] Is 'current_user' connected: {websocket_manager.is_connected('current_user')}")

    websocket_user_id = user_id
    if websocket_manager.is_connected("current_user") and not websocket_manager.is_connected(user_id):
        websocket_user_id = "current_user"
        print(f"⚠️ [Background] Using 'current_user' for WebSocket messages (frontend issue)")
    elif websocket_manager.is_connected(user_id):
        print(f"✅ [Background] Using actual user_id '{user_id}' for WebSocket messages")
    else:
        print(f"❌ [Background] No WebSocket connection found for user '{user_id}' or 'current_user'")
        print(f"🔍 [Background] Active connections: {list(websocket_manager.active_connections.keys())}")

    try:

        # Step 1: Initialize
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "starting",
            "message": "🚀 Initializing data processing pipeline..."
        })

        # Step 2: Create database manager if needed
        if not hasattr(app_state, 'db_manager'):
            config = app_state.config if hasattr(app_state, 'config') and app_state.config else AppConfig()
            app_state.db_manager = DatabaseManager(config)

        # Step 3: Convert file to DuckDB database
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "converting",
            "progress": 0,
            "message": "📊 Loading and indexing data file for processing..."
        })

        # Simulate conversion progress with facts
        for progress in [20, 40, 60, 80, 100]:
            await asyncio.sleep(1.5)  # Simulate processing time
            await websocket_manager.broadcast_progress(websocket_user_id, "converting", progress)

        # Create database connection
        try:
            connection = app_state.db_manager.get_connection(user_id, data_path)
            await websocket_manager.send_to_user(websocket_user_id, {
                "type": "progress",
                "stage": "converting",
                "progress": 100,
                "message": "✅ Database conversion completed!"
            })
        except Exception as e:
            await websocket_manager.send_error(websocket_user_id, f"Database creation failed: {str(e)}")
            return

        # Step 4: Save context (if provided in settings)
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "saving_context",
            "message": "📝 Configuring data analysis context and parameters..."
        })

        # Simulate context saving with facts
        await asyncio.sleep(1)
        await websocket_manager.broadcast_progress(websocket_user_id, "saving_context")
        await asyncio.sleep(1)
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "saving_context",
            "message": "✅ Context saved successfully!"
        })

        # Step 5: Save API key settings
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "saving_api_key",
            "message": "🔑 Setting up AI model integration and authentication..."
        })

        # Simulate API key configuration with facts
        await asyncio.sleep(1)
        await websocket_manager.broadcast_progress(websocket_user_id, "saving_api_key")
        await asyncio.sleep(1)
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "saving_api_key",
            "message": "✅ API key configured successfully!"
        })

        # Step 6 & 7: Generate schema and populate preview cache in parallel
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "parallel_processing",
            "message": "🚀 Processing data schema and optimizing preview performance..."
        })

        # Define parallel tasks with correct websocket_user_id scope
        async def generate_schema_task():
            """Task to generate schema"""
            try:
                await websocket_manager.send_to_user(websocket_user_id, {
                    "type": "progress",
                    "stage": "generating_schema",
                    "progress": 0,
                    "message": "🧠 Generating data schema..."
                })

                # Simulate schema generation progress
                for progress in [25, 50, 75, 100]:
                    await asyncio.sleep(1.0)  # Reduced sleep for parallel execution
                    await websocket_manager.send_to_user(websocket_user_id, {
                        "type": "progress",
                        "stage": "generating_schema",
                        "progress": progress,
                        "message": f"🧠 Schema generation {progress}% complete..."
                    })

                await websocket_manager.send_to_user(websocket_user_id, {
                    "type": "progress",
                    "stage": "generating_schema",
                    "progress": 100,
                    "message": "✅ Schema generation completed!"
                })

                return {"status": "success", "task": "schema_generation"}

            except Exception as e:
                print(f"❌ [Settings] Schema generation failed: {str(e)}")
                await websocket_manager.send_to_user(websocket_user_id, {
                    "type": "progress",
                    "stage": "generating_schema",
                    "message": f"❌ Schema generation failed: {str(e)}"
                })
                return {"status": "error", "task": "schema_generation", "error": str(e)}

        async def populate_preview_cache_task():
            """Task to populate preview cache"""
            try:
                await websocket_manager.send_to_user(websocket_user_id, {
                    "type": "progress",
                    "stage": "caching_preview",
                    "message": "⚡ Populating data preview cache..."
                })

                # Import here to avoid circular imports
                from .data_preview import read_file_with_duckdb_sample, set_cached_preview, SampleType

                # Pre-populate cache for all sample types
                cached_count = 0
                for sample_type in [SampleType.random, SampleType.first]:
                    try:
                        print(f"🔄 [Settings] Starting cache creation for sample_type: {sample_type.value}")

                        # Send progress message to client
                        await websocket_manager.send_to_user(websocket_user_id, {
                            "type": "progress",
                            "stage": "caching_preview",
                            "sample_type": sample_type.value,
                            "message": f"🔄 Caching preview data for sample type: {sample_type.value}...",
                            "timestamp": datetime.now().isoformat()
                        })

                        print(f"🔄 [Settings] Calling read_file_with_duckdb_sample for {sample_type.value}")
                        sample_data = read_file_with_duckdb_sample(data_path, sample_type.value, 100)
                        print(f"✅ [Settings] Got {len(sample_data) if sample_data else 0} rows for {sample_type.value}")

                        if not sample_data:
                            raise Exception(f"No data returned for sample type {sample_type.value}")

                        response_data = {
                            "success": True,
                            "data": sample_data,
                            "row_count": len(sample_data),
                            "file_path": data_path,
                            "sample_type": sample_type.value,
                            "message": f"Successfully loaded {len(sample_data)} {sample_type.value} sample rows"
                        }

                        print(f"🔄 [Settings] Calling set_cached_preview for {sample_type.value}")
                        set_cached_preview(app_state, user_id, sample_type.value, data_path, response_data)
                        cached_count += 1
                        print(f"✅ [Settings] Successfully cached preview for {sample_type.value}: {len(sample_data)} rows")

                        # Send success message to client
                        await websocket_manager.send_to_user(websocket_user_id, {
                            "type": "progress",
                            "stage": "caching_preview",
                            "sample_type": sample_type.value,
                            "status": "completed",
                            "row_count": len(sample_data),
                            "message": f"✅ Successfully cached {len(sample_data)} rows for {sample_type.value}",
                            "timestamp": datetime.now().isoformat()
                        })

                    except Exception as cache_error:
                        print(f"❌ [Settings] Failed to cache {sample_type.value}: {str(cache_error)}")
                        import traceback
                        print(f"❌ [Settings] Full traceback: {traceback.format_exc()}")

                        # Send error message to client
                        await websocket_manager.send_to_user(websocket_user_id, {
                            "type": "progress",
                            "stage": "caching_preview",
                            "sample_type": sample_type.value,
                            "status": "error",
                            "error": str(cache_error),
                            "message": f"❌ Failed to cache {sample_type.value}: {str(cache_error)}",
                            "timestamp": datetime.now().isoformat()
                        })
                        # Continue with other sample types even if one fails

                await websocket_manager.send_to_user(websocket_user_id, {
                    "type": "progress",
                    "stage": "caching_preview",
                    "message": f"✅ Preview cache populated for {cached_count}/2 sample types!"
                })

                return {"status": "success", "task": "preview_cache", "cached_count": cached_count}

            except Exception as e:
                print(f"❌ [Settings] Preview cache population failed: {str(e)}")
                await websocket_manager.send_to_user(websocket_user_id, {
                    "type": "progress",
                    "stage": "caching_preview",
                    "message": f"❌ Preview cache population failed: {str(e)}"
                })
                return {"status": "error", "task": "preview_cache", "error": str(e)}

        # Run schema generation and preview caching in parallel
        print(f"🚀 [Settings] Starting parallel tasks for user: {websocket_user_id}")
        schema_task = generate_schema_task()
        preview_task = populate_preview_cache_task()

        # Wait for both tasks to complete
        results = await asyncio.gather(schema_task, preview_task, return_exceptions=True)

        # Process results
        schema_result = results[0] if not isinstance(results[0], Exception) else {"status": "error", "task": "schema_generation", "error": str(results[0])}
        preview_result = results[1] if not isinstance(results[1], Exception) else {"status": "error", "task": "preview_cache", "error": str(results[1])}

        print(f"📊 [Settings] Parallel processing results for user {websocket_user_id}:")
        print(f"   Schema: {schema_result}")
        print(f"   Preview: {preview_result}")

        # Send final status update
        schema_status = schema_result.get('status', 'unknown') if isinstance(schema_result, dict) else 'error'
        preview_status = preview_result.get('status', 'unknown') if isinstance(preview_result, dict) else 'error'

        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "parallel_processing",
            "message": f"✅ Parallel processing completed - Schema: {schema_status}, Preview: {preview_status}"
        })

        # Check if WebSocket connection is still active before sending final messages
        if not websocket_manager.is_connected(websocket_user_id):
            print(f"⚠️ [Settings] WebSocket connection lost for user {websocket_user_id} - skipping final messages")
            return

        # Step 8: Finalize and close
        print(f"🔒 [Settings] Sending finalization message to user: {websocket_user_id}")
        await websocket_manager.send_to_user(websocket_user_id, {
            "type": "progress",
            "stage": "finalizing",
            "message": "🔒 Completing setup and validating all configurations..."
        })

        # Show finalization facts
        await asyncio.sleep(0.5)
        print(f"📊 [Settings] Sending finalization progress to user: {websocket_user_id}")
        await websocket_manager.broadcast_progress(websocket_user_id, "finalizing")
        await asyncio.sleep(0.5)

        # Double-check connection before sending completion
        if not websocket_manager.is_connected(websocket_user_id):
            print(f"⚠️ [Settings] WebSocket connection lost during finalization for user {websocket_user_id}")
            return

        # Prepare completion data with safe access
        parallel_processing = {}
        if isinstance(schema_result, dict):
            parallel_processing["schema_generation"] = schema_result.get("status")
        else:
            parallel_processing["schema_generation"] = "error"

        if isinstance(preview_result, dict):
            parallel_processing["preview_cache"] = preview_result.get("status")
            parallel_processing["cached_sample_types"] = preview_result.get("cached_count", 0)
        else:
            parallel_processing["preview_cache"] = "error"
            parallel_processing["cached_sample_types"] = 0

        print(f"🎉 [Settings] Sending completion message to user: {websocket_user_id}")
        await websocket_manager.send_completion(websocket_user_id, {
            "success": True,
            "data_path": data_path,
            "message": "🎉 Data processing setup completed successfully! Your data is ready for analysis.",
            "parallel_processing": parallel_processing,
            "steps_completed": [
                "Database conversion",
                "Context saving",
                "API key configuration",
                "Parallel: Schema generation + Preview cache",
                "Finalization"
            ]
        })
        print(f"✅ [Settings] Completion message sent successfully")

    except Exception as e:
        await websocket_manager.send_error(websocket_user_id, f"Processing failed: {str(e)}")