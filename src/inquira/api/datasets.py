from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Any
from pathlib import Path
import duckdb
import os
from .auth import get_current_user
from ..database.database import (
    list_datasets, 
    get_dataset_by_table_name, 
    delete_dataset, 
    upsert_dataset
)
from ..core.path_utils import (
    get_database_path,
    get_dataset_dir,
    get_legacy_schemas_dir,
    get_username_for_user
)
from ..core.logger import logprint

router = APIRouter(prefix="/datasets", tags=["Datasets"])

class DatasetResponse(BaseModel):
    id: int
    file_path: str
    table_name: str
    row_count: Optional[int] = None
    file_size_mb: float
    created_at: str
    updated_at: str
    is_active: bool = False

class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]

class DatasetHealthResponse(BaseModel):
    table_name: str
    healthy: bool
    row_count: Optional[int] = None
    error: Optional[str] = None

class DatasetDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_files: List[str] = []

@router.get("/list", response_model=DatasetListResponse)
def list_datasets_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """List all available datasets for the current user"""
    user_id = current_user["user_id"]
    datasets = list_datasets(user_id)
    
    # Enrich with additional info if needed
    response_datasets = []
    
    # Get currently active dataset path
    from ..database.database import get_user_settings
    settings = get_user_settings(user_id)
    active_path = settings.get("data_path")
    
    for ds in datasets:
        is_active = (ds["file_path"] == active_path)
        
        response_datasets.append(DatasetResponse(
            id=ds["id"],
            file_path=ds["file_path"],
            table_name=ds["table_name"],
            row_count=ds["row_count"],
            file_size_mb=round(ds["file_size"] / (1024 * 1024), 2) if ds["file_size"] else 0.0,
            created_at=str(ds["created_at"]),
            updated_at=str(ds["updated_at"]),
            is_active=is_active
        ))
    
    return DatasetListResponse(datasets=response_datasets)

@router.get("/{table_name}/health", response_model=DatasetHealthResponse)
def check_dataset_health(
    table_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if the dataset table exists and is readable in DuckDB"""
    user_id = current_user["user_id"]
    
    # Confirm dataset exists in catalog first
    ds = get_dataset_by_table_name(user_id, table_name)
    if not ds:
        return DatasetHealthResponse(
            table_name=table_name,
            healthy=False,
            error="Dataset not found in catalog"
        )
        
    # Try to query the DuckDB table
    try:
        db_path = get_database_path(user_id)
        
        if not db_path.exists():
            return DatasetHealthResponse(
                table_name=table_name,
                healthy=False,
                error="DuckDB database file does not exist"
            )
        
        conn = duckdb.connect(str(db_path), read_only=True)
        # Check if table exists and get row count
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        conn.close()
        
        return DatasetHealthResponse(
            table_name=table_name,
            healthy=True,
            row_count=result[0] if result else 0
        )
    except Exception as e:
        return DatasetHealthResponse(
            table_name=table_name,
            healthy=False,
            error=str(e)
        )

@router.delete("/{table_name}", response_model=DatasetDeleteResponse)
def delete_dataset_endpoint(
    table_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a dataset and its associated files (schema, cache, DuckDB table)"""
    from datetime import datetime
    
    # Debug log file for tracing delete operations
    debug_log_path = Path.home() / ".inquira" / "logs" / "delete_debug.log"
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def debug_log(msg: str):
        with open(debug_log_path, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
        logprint(msg)
    
    user_id = current_user["user_id"]
    debug_log(f"🗑️ DELETE START: table_name={table_name}, user_id={user_id}")
    
    ds = get_dataset_by_table_name(user_id, table_name)
    
    if not ds:
        debug_log(f"❌ DELETE FAILED: Dataset '{table_name}' not found in catalog")
        raise HTTPException(status_code=404, detail=f"Dataset '{table_name}' not found")
    
    debug_log(f"📋 Found dataset: file_path={ds.get('file_path')}, schema_path={ds.get('schema_path')}")
    
    deleted_files = []
    
    # 1. Clean up new structure: ~/.inquira/{username}/{table_name}/
    try:
        dataset_dir = get_dataset_dir(user_id, table_name, create=False)  # Don't create!
        debug_log(f"📂 Dataset dir path: {dataset_dir}")
        debug_log(f"📂 Dataset dir exists: {dataset_dir.exists()}")
        
        if dataset_dir.exists():
            # List contents before delete
            contents = list(dataset_dir.iterdir())
            debug_log(f"📂 Directory contents before delete: {[str(c) for c in contents]}")
            
            # Delete contents
            import shutil
            shutil.rmtree(dataset_dir)
            deleted_files.append(f"Directory: {dataset_dir}")
            debug_log(f"✅ Deleted directory: {dataset_dir}")
            
            # Verify deletion
            debug_log(f"📂 Directory exists after delete: {dataset_dir.exists()}")
        else:
            debug_log(f"⚠️ Dataset directory does not exist: {dataset_dir}")
    except Exception as e:
        debug_log(f"❌ Failed to delete dataset directory: {e}")
        logprint(f"⚠️ [Datasets] Failed to delete dataset directory: {e}", level="warning")

    # 2. Delete schema file if referenced explicitly (legacy or new)
    if ds.get("schema_path"):
        schema_path = Path(ds["schema_path"])
        debug_log(f"📋 Schema path from catalog: {schema_path}")
        debug_log(f"📋 Schema file exists: {schema_path.exists()}")
        if schema_path.exists():
            try:
                schema_path.unlink()
                deleted_files.append(str(schema_path))
                debug_log(f"✅ Deleted schema file: {schema_path}")
            except Exception as e:
                debug_log(f"❌ Failed to delete schema file: {e}")
    
    # 3. Delete legacy schema files
    try:
        from ..database.schema_storage import get_schema_filename, get_legacy_schemas_dir as get_legacy_dir
        legacy_dir = get_legacy_dir(user_id)
        if ds.get("file_path"):
            legacy_filename = get_schema_filename(user_id, ds["file_path"])
            legacy_schema_path = legacy_dir / legacy_filename
            debug_log(f"📋 Legacy schema path: {legacy_schema_path}")
            debug_log(f"📋 Legacy schema exists: {legacy_schema_path.exists()}")
            if legacy_schema_path.exists():
                legacy_schema_path.unlink()
                deleted_files.append(f"Legacy schema: {legacy_schema_path}")
                debug_log(f"✅ Deleted legacy schema: {legacy_schema_path}")
    except Exception as e:
        debug_log(f"⚠️ Legacy schema cleanup error: {e}")
    
    # 4. Drop table from DuckDB
    try:
        db_path = get_database_path(user_id)
        debug_log(f"🗄️ DuckDB path: {db_path}")
        debug_log(f"🗄️ DuckDB exists: {db_path.exists()}")
        if db_path.exists():
            conn = duckdb.connect(str(db_path))
            
            # List tables before drop
            tables_before = conn.execute("SHOW TABLES").fetchall()
            debug_log(f"🗄️ Tables before drop: {[t[0] for t in tables_before]}")
            
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # List tables after drop
            tables_after = conn.execute("SHOW TABLES").fetchall()
            debug_log(f"🗄️ Tables after drop: {[t[0] for t in tables_after]}")
            
            conn.close()
            deleted_files.append(f"DuckDB table: {table_name}")
            debug_log(f"✅ Dropped DuckDB table: {table_name}")
    except Exception as e:
        debug_log(f"❌ Failed to drop table: {e}")
        logprint(f"⚠️ [Datasets] Failed to drop table: {e}", level="warning")
    
    # 4.5 Check if this was the active dataset and clear settings if so
    try:
        from ..database.database import get_user_settings, save_user_settings
        settings = get_user_settings(user_id)
        active_path = settings.get("data_path")
        
        if active_path and ds.get("file_path") and active_path == ds["file_path"]:
            debug_log(f"🧹 Deleting active dataset. Clearing user settings.")
            settings["data_path"] = None
            settings["schema_path"] = None
            settings["context"] = None
            save_user_settings(user_id, settings)
            debug_log(f"✅ User settings cleared")
    except Exception as e:
        debug_log(f"⚠️ Failed to clear user settings: {e}")
        logprint(f"⚠️ [Datasets] Failed to clear user settings: {e}", level="warning")

    # 5. Delete from datasets catalog
    success = delete_dataset(user_id, table_name)
    debug_log(f"📋 Catalog delete result: {success}")
    
    debug_log(f"🗑️ DELETE COMPLETE: deleted_files={deleted_files}")
    
    if success:
        return DatasetDeleteResponse(
            success=True,
            message=f"Dataset '{table_name}' deleted successfully",
            deleted_files=deleted_files
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to delete dataset from catalog")


class DatasetRefreshRequest(BaseModel):
    regenerate_schema: bool = True  # Whether to also regenerate schema


class DatasetRefreshResponse(BaseModel):
    success: bool
    message: str
    row_count: Optional[int] = None
    schema_regenerated: bool = False


@router.post("/{table_name}/refresh", response_model=DatasetRefreshResponse)
def refresh_dataset_endpoint(
    table_name: str,
    request: DatasetRefreshRequest = DatasetRefreshRequest(),
    current_user: dict = Depends(get_current_user)
):
    """
    Refresh a dataset by reimporting from source file.
    Creates a backup first, restores on failure.
    """
    user_id = current_user["user_id"]
    logprint(f"🔄 [Datasets] Refreshing dataset: {table_name} for user {user_id}")
    
    # 1. Get dataset info
    ds = get_dataset_by_table_name(user_id, table_name)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{table_name}' not found")
    
    file_path = ds.get("file_path")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=400, detail=f"Source file not found: {file_path}")
    
    # 2. Get database connection
    db_path = get_database_path(user_id)
    if not db_path.exists():
        raise HTTPException(status_code=400, detail="Database not found")
    
    conn = duckdb.connect(str(db_path))
    backup_table = f"{table_name}_backup"
    
    try:
        # 3. Create backup
        logprint(f"📦 [Datasets] Creating backup table: {backup_table}")
        conn.execute(f"DROP TABLE IF EXISTS {backup_table}")
        conn.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}")
        
        # 4. Drop original and reimport
        logprint(f"🔄 [Datasets] Dropping and reimporting: {table_name}")
        conn.execute(f"DROP TABLE {table_name}")
        
        # Determine file type and import
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.csv':
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
        elif file_ext == '.parquet':
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{file_path}')")
        elif file_ext in ['.xlsx', '.xls']:
            # For Excel, use pandas as intermediary
            import pandas as pd
            df = pd.read_excel(file_path)
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        # 5. Get new row count
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        new_row_count = result[0] if result else 0
        
        # 6. Drop backup (success!)
        logprint(f"✅ [Datasets] Refresh successful, dropping backup")
        conn.execute(f"DROP TABLE IF EXISTS {backup_table}")
        conn.close()
        
        # 7. Update dataset catalog
        upsert_dataset(
            user_id=user_id,
            file_path=file_path,
            table_name=table_name,
            row_count=new_row_count,
            file_size_mb=Path(file_path).stat().st_size / (1024 * 1024)
        )
        
        # 8. Optionally regenerate schema
        schema_regenerated = False
        if request.regenerate_schema:
            try:
                from .schemas import _generate_schema_internal
                from ..database.database import get_user_settings
                
                settings = get_user_settings(user_id)
                api_key = settings.get("api_key")
                context = settings.get("context")
                
                if api_key:
                    logprint(f"🔄 [Datasets] Regenerating schema...")
                    # Create a minimal app_state-like dict with necessary keys
                    app_state = {"api_key": api_key}
                    _generate_schema_internal(
                        user_id=user_id,
                        filepath=file_path,
                        context=context,
                        api_key=api_key,
                        app_state=app_state,
                        force_regenerate=True
                    )
                    schema_regenerated = True
                else:
                    logprint(f"⚠️ [Datasets] No API key found, skipping schema regeneration", level="warning")
            except Exception as schema_err:
                logprint(f"⚠️ [Datasets] Schema regeneration failed: {schema_err}", level="warning")
        
        return DatasetRefreshResponse(
            success=True,
            message=f"Dataset '{table_name}' refreshed successfully with {new_row_count} rows",
            row_count=new_row_count,
            schema_regenerated=schema_regenerated
        )
        
    except Exception as e:
        # RESTORE from backup
        logprint(f"❌ [Datasets] Refresh failed, restoring from backup: {e}", level="error")
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"ALTER TABLE {backup_table} RENAME TO {table_name}")
            logprint(f"✅ [Datasets] Restored {table_name} from backup")
        except Exception as restore_err:
            logprint(f"❌ [Datasets] Restore also failed: {restore_err}", level="error")
        finally:
            conn.close()
        
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}. Original data restored.")
