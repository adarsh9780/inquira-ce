import duckdb
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any, Optional
import os
import pickle
from pathlib import Path
from enum import Enum
from datetime import datetime
from .auth import get_current_user
from ..database.database import get_user_settings
from ..database.schema_storage import load_schema, derive_table_name
from ..core.logger import logprint
from ..database.sql_library import get_sql
from ..core.path_utils import (
    get_preview_cache_path,
    get_legacy_schemas_dir,
    list_dataset_dirs,
    PREVIEW_CACHE_PREFIX,
    PREVIEW_CACHE_EXT
)

class SampleType(str, Enum):
    random = "random"
    first = "first"

router = APIRouter(tags=["Data Preview"])

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

def get_preview_cache_file_path(user_id: str, sample_type: str, data_path: str = None) -> Path:
    """Get the file path for a user's preview cache file
    
    Now uses per-dataset folders: ~/.inquira/{username}/{table_name}/preview_{sample_type}.pkl
    """
    if data_path:
        table_name = derive_table_name(data_path)
        try:
            return get_preview_cache_path(user_id, table_name, sample_type)
        except Exception:
            # Fallback path if user lookup fails (unlikely)
            pass
            
    # Fallback to legacy path if no data_path or error
    import hashlib
    user_dir = get_legacy_schemas_dir(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    if data_path:
        path_hash = hashlib.md5(data_path.encode()).hexdigest()[:12]
        filename = f"{user_id}_preview_{sample_type}_{path_hash}.pkl"
    else:
        filename = f"{user_id}_preview_{sample_type}.pkl"
    
    return user_dir / filename

def get_cached_preview(app_state, user_id: str, sample_type: str, data_path: str) -> Optional[Dict[str, Any]]:
    """Get cached preview data from pickle file if available"""
    try:
        cache_file = get_preview_cache_file_path(user_id, sample_type, data_path)

        if not cache_file.exists():
            return None

        # Check if cache is still valid (file hasn't been modified since cache was created)
        if os.path.exists(data_path):
            data_mtime = os.path.getmtime(data_path)
            cache_mtime = os.path.getmtime(cache_file)

            # If data file is newer than cache, invalidate cache
            if data_mtime > cache_mtime:
                logprint(f"⚠️ [Data Preview] Cache invalidated - data file modified since cache creation")
                cache_file.unlink()  # Delete invalid cache
                return None

        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)

        # Verify the cached data is for the correct file path
        if cached_data.get('file_path') != data_path:
            logprint(f"⚠️ [Data Preview] Cache file path mismatch, invalidating cache")
            cache_file.unlink()
            return None

        logprint(f"✅ [Data Preview] Loaded cached preview from: {cache_file}")
        return cached_data

    except Exception as e:
        logprint(f"⚠️ [Data Preview] Error loading cache file: {str(e)}", level="warning")
        # Try to clean up corrupted cache file
        try:
            cache_file = get_preview_cache_file_path(user_id, sample_type, data_path)
            if cache_file.exists():
                cache_file.unlink()
        except:
            pass
        return None

def set_cached_preview(app_state, user_id: str, sample_type: str, data_path: str, preview_data: Dict[str, Any]):
    """Cache preview data to pickle file"""
    try:
        cache_file = get_preview_cache_file_path(user_id, sample_type, data_path)

        # Ensure the user directory exists
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata to the cached data
        cache_data = preview_data.copy()
        cache_data['_cache_metadata'] = {
            'created_at': datetime.now().isoformat(),
            'data_path': data_path,
            'sample_type': sample_type,
            'user_id': user_id
        }

        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)

        logprint(f"✅ [Data Preview] Saved cache to: {cache_file}")

    except Exception as e:
        logprint(f"❌ [Data Preview] Error saving cache file: {str(e)}", level="error")

def clear_user_preview_cache(app_state, user_id: str):
    """Clear all cached preview data for a user by deleting pickle files"""
    deleted_count = 0
    
    # 1. Clear from separate dataset dirs (New Structure)
    try:
        dataset_dirs = list_dataset_dirs(user_id)
        for d in dataset_dirs:
            for cache_file in d.glob(f"{PREVIEW_CACHE_PREFIX}*{PREVIEW_CACHE_EXT}"):
                try:
                    cache_file.unlink()
                    deleted_count += 1
                except Exception:
                    pass
    except Exception as e:
         logprint(f"⚠️ [Data Preview] Error clearing new structure cache: {str(e)}", level="warning")

    # 2. Clear from legacy schemas dir
    try:
        user_dir = get_legacy_schemas_dir(user_id)
        if user_dir.exists():
            for cache_file in user_dir.glob(f"{user_id}_preview_*.pkl"):
                try:
                    cache_file.unlink()
                    deleted_count += 1
                except Exception:
                    pass
    except Exception as e:
        logprint(f"⚠️ [Data Preview] Error clearing legacy cache: {str(e)}", level="warning")

    logprint(f"🗑️ [Data Preview] Cleared {deleted_count} cached files for user: {user_id}")

def get_file_type(file_path: str) -> str:
    """Determine file type based on extension"""
    lower = file_path.lower()
    if lower.endswith('.csv'):
        return 'csv'
    elif lower.endswith('.xlsx'):
        return 'xlsx'
    elif lower.endswith('.xls'):
        return 'xls'
    elif lower.endswith('.parquet'):
        return 'parquet'
    elif lower.endswith('.json'):
        return 'json'
    else:
        # Try to detect from content or default to CSV
        return 'csv'

def _try_load_excel_extension(con: duckdb.DuckDBPyConnection) -> bool:
    """Attempt to LOAD (and if needed INSTALL) DuckDB excel extension.
    Returns True on success, False on failure.
    """
    try:
        con.execute("LOAD excel")
        return True
    except duckdb.Error:
        try:
            # INSTALL may require network; ignore errors and fallback if it fails
            con.execute("INSTALL excel")
            con.execute("LOAD excel")
            return True
        except duckdb.Error:
            return False

def read_file_with_duckdb(file_path: str, sample_size: int = 100) -> List[Dict[str, Any]]:
    """
    Read a sample of data from various file formats using DuckDB
    Optimized to avoid loading entire files into memory
    """
    try:
        if isinstance(file_path, str) and file_path.startswith("browser://"):
            raise HTTPException(
                status_code=400,
                detail="Browser-native datasets are previewed in the frontend runtime."
            )

        file_type = get_file_type(file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found: {file_path}"
            )

        # Connect to DuckDB with memory optimizations
        con = duckdb.connect(database=':memory:')
        con.execute("SET memory_limit='1GB'")
        con.execute("SET threads=1")

        try:
            # Build optimized query based on file type
            if file_type == 'csv':
                query = get_sql('read_csv_sample', file_path=file_path, sample_type='random', sample_size=sample_size)
                describe_query = get_sql('describe_csv', file_path=file_path)
            elif file_type == 'parquet':
                query = get_sql('read_parquet_sample', file_path=file_path, sample_type='random', sample_size=sample_size)
                describe_query = get_sql('describe_parquet', file_path=file_path)
            elif file_type == 'json':
                query = get_sql('read_json_sample', file_path=file_path, sample_type='random', sample_size=sample_size)
                describe_query = get_sql('describe_json', file_path=file_path)
            elif file_type == 'xlsx':
                # Prefer DuckDB excel extension to avoid pandas memory usage
                if _try_load_excel_extension(con):
                    query = get_sql('read_xlsx_sample', file_path=file_path, sample_type='random', sample_size=sample_size)
                    describe_query = get_sql('describe_xlsx', file_path=file_path)
                else:
                    # Fallback to pandas if extension unavailable
                    df_sample = pd.read_excel(file_path, nrows=min(1000, sample_size * 10))
                    con.register('temp_df', df_sample)
                    query = get_sql('read_table_sample', table_name='temp_df', sample_type='random', sample_size=sample_size)
                    describe_query = get_sql('describe_table', table_name='temp_df')
            elif file_type == 'xls':
                raise HTTPException(
                    status_code=400,
                    detail=".xls files are not supported. Please convert to .xlsx or csv."
                )
            else:
                # Fallback to CSV
                query = get_sql('read_csv_sample', file_path=file_path, sample_type='random', sample_size=sample_size)
                describe_query = get_sql('describe_csv', file_path=file_path)

            # Get sample data
            result = con.execute(query).fetchall()

            # Get column names
            column_names = [desc[0] for desc in con.execute(describe_query).fetchall()]

            # Convert to list of dictionaries
            data = []
            for row in result:
                row_dict: Dict[str, Any] = {}
                for i, col_name in enumerate(column_names):
                    # Handle different data types
                    value = row[i]
                    if value is None:
                        row_dict[col_name] = None
                    elif isinstance(value, (int, float)):
                        row_dict[col_name] = value
                    else:
                        row_dict[col_name] = str(value)
                data.append(row_dict)

            return data

        finally:
            con.close()

    except HTTPException:
        raise
    except duckdb.Error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Database error while reading file: {str(e)}"
        )
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="The file appears to be empty or contains no valid data"
        )
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing file: {str(e)}"
        )
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied accessing file: {file_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error reading file: {str(e)}"
        )

# ... (Previous schema retrieval code is identical, except imports)
# I will just write the rest of the file exactly as it was, but ensuring imports are correct.

@router.get("/data/schema")
async def get_data_schema(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get schema information for the user's data file
    First checks for existing saved schema, falls back to generating new one if needed
    """
    try:
        # Get user's settings
        user_id = current_user["user_id"]
        user_settings = get_user_settings(user_id)
        data_path = user_settings.get("data_path")

        if not data_path:
            raise HTTPException(
                status_code=400,
                detail="No data file path configured. Please set your data path in settings."
            )

        # First, try to load existing schema (will try both new and legacy internally)
        existing_schema = load_schema(user_id, data_path)
        if existing_schema:
            logprint(f"✅ [Data Preview] Using existing schema for: {data_path}")
            schema_info = [
                {
                    "name": col.name,
                    "type": col.data_type,
                    "description": col.description,
                    "nullable": True,
                    "sample_value": str(col.sample_values[0]) if col.sample_values else None
                }
                for col in existing_schema.columns
            ]

            return {
                "success": True,
                "schema": schema_info,
                "file_path": data_path,
                "context": existing_schema.context,
                "created_at": existing_schema.created_at,
                "updated_at": existing_schema.updated_at,
                "message": f"Successfully loaded existing schema for {len(schema_info)} columns"
            }

        # If no existing schema, get basic schema information from file
        logprint(f"⚠️ [Data Preview] No existing schema found, getting basic schema for: {data_path}")
        schema_info = get_file_schema(data_path)

        return {
            "success": True,
            "schema": schema_info,
            "file_path": data_path,
            "message": f"Successfully retrieved basic schema for {len(schema_info)} columns (no saved schema found)"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving data schema: {str(e)}"
        )

@router.get("/data/preview")
async def get_data_preview(
    sample_type: SampleType = SampleType.random,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
) -> Dict[str, Any]:
    """
    Get a preview of the user's data file with different sampling options

    Returns cached data if available, otherwise generates new preview.
    """
    try:
        # Get user's settings
        user_id = current_user["user_id"]
        user_settings = get_user_settings(user_id)
        data_path = user_settings.get("data_path")

        if not data_path:
            raise HTTPException(
                status_code=400,
                detail="No data file path configured. Please set your data path in settings."
            )

        # Check cache first
        cached_data = get_cached_preview(app_state, user_id, sample_type.value, data_path)
        if cached_data:
            logprint(f"✅ [Data Preview] Returning cached preview for: {user_id}:{data_path}:{sample_type.value}")
            # Send cache hit message to WebSocket if connected
            try:
                from ..services.websocket_manager import websocket_manager
                websocket_user_id = user_id if websocket_manager.is_connected(user_id) else ("current_user" if websocket_manager.is_connected("current_user") else None)
                if websocket_user_id:
                    import asyncio
                    # Send message asynchronously without blocking
                    asyncio.create_task(
                        websocket_manager.send_to_user(websocket_user_id, {
                            "type": "cache_hit",
                            "sample_type": sample_type.value,
                            "data_path": data_path,
                            "row_count": cached_data.get("row_count", 0),
                            "message": f"⚡ Using cached preview data for {sample_type.value} ({cached_data.get('row_count', 0)} rows)",
                            "timestamp": datetime.now().isoformat()
                        })
                    )
            except Exception as e:
                logprint(f"⚠️ [Data Preview] Could not send cache hit message: {str(e)}", level="warning")

            return cached_data

        # Generate new preview data
        logprint(f"⚠️ [Data Preview] No cached preview found, generating new for: {user_id}:{data_path}:{sample_type.value}")
        sample_data = read_file_with_duckdb_sample(data_path, sample_type.value, 100)

        # Prepare response
        response_data = {
            "success": True,
            "data": sample_data,
            "row_count": len(sample_data),
            "file_path": data_path,
            "sample_type": sample_type.value,
            "message": f"Successfully loaded {len(sample_data)} {sample_type.value} sample rows"
        }

        # Cache the response
        set_cached_preview(app_state, user_id, sample_type.value, data_path, response_data)

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving data preview: {str(e)}"
        )

@router.post("/data/preview/refresh")
async def refresh_data_preview(
    sample_type: SampleType = SampleType.random,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
) -> Dict[str, Any]:
    """
    Refresh the cached preview data for the user's data file

    Forces regeneration of preview data and updates the cache.
    """
    try:
        # Get user's settings
        user_id = current_user["user_id"]
        user_settings = get_user_settings(user_id)
        data_path = user_settings.get("data_path")

        if not data_path:
            raise HTTPException(
                status_code=400,
                detail="No data file path configured. Please set your data path in settings."
            )

        # Send refresh start message to WebSocket if connected
        try:
            from ..services.websocket_manager import websocket_manager
            websocket_user_id = user_id if websocket_manager.is_connected(user_id) else ("current_user" if websocket_manager.is_connected("current_user") else None)
            if websocket_user_id:
                import asyncio
                asyncio.create_task(
                    websocket_manager.send_to_user(websocket_user_id, {
                        "type": "cache_refresh",
                        "sample_type": sample_type.value,
                        "data_path": data_path,
                        "message": f"🔄 Refreshing cached preview data for {sample_type.value}...",
                        "timestamp": datetime.now().isoformat()
                    })
                )
        except Exception as e:
            logprint(f"⚠️ [Data Preview] Could not send refresh start message: {str(e)}")

        # Generate fresh preview data
        logprint(f"🔄 [Data Preview] Refreshing preview for: {user_id}:{data_path}:{sample_type.value}")
        sample_data = read_file_with_duckdb_sample(data_path, sample_type.value, 100)

        # Prepare response
        response_data = {
            "success": True,
            "data": sample_data,
            "row_count": len(sample_data),
            "file_path": data_path,
            "sample_type": sample_type.value,
            "message": f"Successfully refreshed {len(sample_data)} {sample_type.value} sample rows"
        }

        # Update cache with fresh data
        set_cached_preview(app_state, user_id, sample_type.value, data_path, response_data)

        # Send refresh completion message to WebSocket if connected
        try:
            from ..services.websocket_manager import websocket_manager
            websocket_user_id = user_id if websocket_manager.is_connected(user_id) else ("current_user" if websocket_manager.is_connected("current_user") else None)
            if websocket_user_id:
                import asyncio
                asyncio.create_task(
                    websocket_manager.send_to_user(websocket_user_id, {
                        "type": "cache_refresh",
                        "sample_type": sample_type.value,
                        "data_path": data_path,
                        "status": "completed",
                        "row_count": len(sample_data),
                        "message": f"✅ Successfully refreshed cache for {sample_type.value} ({len(sample_data)} rows)",
                        "timestamp": datetime.now().isoformat()
                    })
                )
        except Exception as e:
            logprint(f"⚠️ [Data Preview] Could not send refresh completion message: {str(e)}")

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing data preview: {str(e)}"
        )

@router.delete("/data/preview/cache")
async def clear_preview_cache(
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
) -> Dict[str, Any]:
    """
    Clear all cached preview data for the current user
    """
    try:
        user_id = current_user["user_id"]
        clear_user_preview_cache(app_state, user_id)

        return {
            "success": True,
            "message": f"Successfully cleared preview cache for user: {user_id}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing preview cache: {str(e)}"
        )

def get_file_schema(file_path: str) -> List[Dict[str, Any]]:
    """
    Get schema information (column names and types) from a file
    Optimized to avoid loading entire files into memory
    """
    try:
        if isinstance(file_path, str) and file_path.startswith("browser://"):
            raise HTTPException(
                status_code=400,
                detail="Browser-native datasets are schema-managed through /schemas endpoints."
            )

        file_type = get_file_type(file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found: {file_path}"
            )

        # Connect to DuckDB with memory optimizations
        con = duckdb.connect(database=':memory:')
        con.execute("SET memory_limit='512MB'")  # Smaller limit for schema
        con.execute("SET threads=1")

        try:
            # Build schema query based on file type
            if file_type == 'csv':
                schema_query = get_sql('describe_csv', file_path=file_path)
                sample_query = get_sql('read_csv_sample', file_path=file_path, sample_type='first', sample_size=5)
            elif file_type == 'parquet':
                schema_query = get_sql('describe_parquet', file_path=file_path)
                sample_query = get_sql('read_parquet_sample', file_path=file_path, sample_type='first', sample_size=5)
            elif file_type == 'json':
                schema_query = get_sql('describe_json', file_path=file_path)
                sample_query = get_sql('read_json_sample', file_path=file_path, sample_type='first', sample_size=5)
            elif file_type == 'xlsx':
                if _try_load_excel_extension(con):
                    schema_query = get_sql('describe_xlsx', file_path=file_path)
                    sample_query = get_sql('read_xlsx_sample', file_path=file_path, sample_type='first', sample_size=5)
                else:
                    df_sample = pd.read_excel(file_path, nrows=10)
                    con.register('temp_df', df_sample)
                    schema_query = get_sql('describe_table', table_name='temp_df')
                    sample_query = get_sql('read_table_sample', table_name='temp_df', sample_type='first', sample_size=5)
            elif file_type == 'xls':
                raise HTTPException(
                    status_code=400,
                    detail=".xls files are not supported. Please convert to .xlsx or csv."
                )
            else:
                # Fallback to CSV
                schema_query = get_sql('describe_csv', file_path=file_path)
                sample_query = get_sql('read_csv_sample', file_path=file_path, sample_type='first', sample_size=5)

            # Get column information
            columns_info = con.execute(schema_query).fetchall()

            # Get sample data for better type inference
            sample_data = con.execute(sample_query).fetchall()
            column_names = [desc[0] for desc in columns_info]

            # Convert to schema format
            schema = []
            for i, col_info in enumerate(columns_info):
                column_name = col_info[0]
                column_type = col_info[1]

                # Get sample value from the sample data
                sample_value = None
                if sample_data and len(sample_data) > 0 and i < len(sample_data[0]):
                    sample_value = sample_data[0][i]

                schema.append({
                    "name": column_name,
                    "type": column_type,
                    "nullable": True,  # DuckDB doesn't provide nullability info easily
                    "sample_value": str(sample_value) if sample_value is not None else None
                })

            return schema

        finally:
            con.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving schema: {str(e)}"
        )

def read_file_with_duckdb_sample(file_path: str, sample_type: str = "random", sample_size: int = 100) -> List[Dict[str, Any]]:
    """
    Read a sample of data from various file formats using DuckDB with different sampling methods
    Optimized to avoid loading entire files into memory
    """
    try:
        if isinstance(file_path, str) and file_path.startswith("browser://"):
            raise HTTPException(
                status_code=400,
                detail="Browser-native datasets are previewed in the frontend runtime."
            )

        file_type = get_file_type(file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found: {file_path}"
            )

        # Connect to DuckDB with memory optimizations
        con = duckdb.connect(database=':memory:')

        # Set memory and performance optimizations
        con.execute("SET memory_limit='1GB'")  # Limit memory usage
        con.execute("SET threads=1")  # Use single thread to reduce memory
        con.execute("SET preserve_insertion_order=false")  # Performance optimization

        try:
            # Build query based on file type and sample type
            if file_type == 'csv':
                query = get_sql('read_csv_sample', file_path=file_path, sample_type=sample_type, sample_size=sample_size)
            elif file_type == 'parquet':
                query = get_sql('read_parquet_sample', file_path=file_path, sample_type=sample_type, sample_size=sample_size)
            elif file_type == 'json':
                query = get_sql('read_json_sample', file_path=file_path, sample_type=sample_type, sample_size=sample_size)
            elif file_type == 'xlsx':
                if _try_load_excel_extension(con):
                    query = get_sql('read_xlsx_sample', file_path=file_path, sample_type=sample_type, sample_size=sample_size)
                else:
                    # Fallback to limited pandas
                    df_sample = pd.read_excel(file_path, nrows=min(1000, sample_size * 10))
                    con.register('temp_df', df_sample)
                    query = get_sql('read_table_sample', table_name='temp_df', sample_type=sample_type, sample_size=sample_size)
            elif file_type == 'xls':
                raise HTTPException(
                    status_code=400,
                    detail=".xls files are not supported. Please convert to .xlsx or csv."
                )
            else:
                # Fallback to CSV
                query = get_sql('read_csv_sample', file_path=file_path, sample_type=sample_type, sample_size=sample_size)

            # Execute the optimized query
            result = con.execute(query).fetchall()

            # Get column names using describe on base source (schema is same regardless of sampling)
            if file_type == 'csv':
                describe_query = get_sql('describe_csv', file_path=file_path)
            elif file_type == 'parquet':
                describe_query = get_sql('describe_parquet', file_path=file_path)
            elif file_type == 'json':
                describe_query = get_sql('describe_json', file_path=file_path)
            elif file_type == 'xlsx' and _try_load_excel_extension(con):
                describe_query = get_sql('describe_xlsx', file_path=file_path)
            else:
                # fallback path for temp_df
                describe_query = get_sql('describe_table', table_name='temp_df')
            column_names = [desc[0] for desc in con.execute(describe_query).fetchall()]

            # Convert to list of dictionaries
            data = []
            for row in result:
                row_dict: Dict[str, Any] = {}
                for i, col_name in enumerate(column_names):
                    # Handle different data types
                    value = row[i]
                    if value is None:
                        row_dict[col_name] = None
                    elif isinstance(value, (int, float)):
                        row_dict[col_name] = value
                    else:
                        row_dict[col_name] = str(value)
                data.append(row_dict)

            return data

        finally:
            con.close()

    except HTTPException:
        raise
    except duckdb.Error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Database error while reading file: {str(e)}"
        )
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="The file appears to be empty or contains no valid data"
        )
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing file: {str(e)}"
        )
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied accessing file: {file_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error reading file: {str(e)}"
        )
