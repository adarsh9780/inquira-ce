from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from .auth import get_current_user
from ..database.database import get_dataset_by_path, list_datasets


router = APIRouter(prefix="/datasets", tags=["Datasets"])


class DatasetInfo(BaseModel):
    data_path: str = Field(description="Original absolute path to the data file")
    table_name: str = Field(description="Stable DuckDB table name used for this file")
    schema_path: Optional[str] = Field(default=None, description="Path to the generated per-file schema JSON")
    file_hash: str = Field(description="Computed fingerprint for this file/version")
    file_size: Optional[int] = Field(default=None, description="Size of the file in bytes")
    source_mtime: Optional[float] = Field(default=None, description="Last modification time of the file (seconds since epoch)")
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)


@router.get("/lookup", response_model=DatasetInfo)
def lookup_dataset(
    data_path: str = Query(..., description="Absolute path to the data file"),
    current_user: dict = Depends(get_current_user)
):
    """Return dataset info (table_name, schema_path, etc.) for the given data_path"""
    user_id = current_user["user_id"]
    ds = get_dataset_by_path(user_id, data_path)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found for the provided data_path")

    return DatasetInfo(
        data_path=ds["file_path"],
        table_name=ds["table_name"],
        schema_path=ds.get("schema_path"),
        file_hash=ds["file_hash"],
        file_size=ds.get("file_size"),
        source_mtime=ds.get("source_mtime"),
        created_at=ds.get("created_at"),
        updated_at=ds.get("updated_at"),
    )


@router.post("/sync")
def sync_duckdb_tables(current_user: dict = Depends(get_current_user)):
    """Scan DuckDB for tables not in catalog and register them"""
    import duckdb
    from pathlib import Path
    from ..database.database import list_datasets
    
    user_id = current_user["user_id"]
    db_path = Path.home() / ".inquira" / user_id / f"{user_id}_data.duckdb"
    
    if not db_path.exists():
        return {"synced": 0, "message": "No DuckDB database found"}
    
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        # Get all tables from DuckDB
        tables_result = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
        duckdb_tables = {row[0] for row in tables_result}
        conn.close()
        
        # Get tables already in catalog
        catalog_datasets = list_datasets(user_id)
        catalog_tables = {ds['table_name'] for ds in catalog_datasets}
        
        # Find tables in DuckDB but not in catalog
        missing_tables = duckdb_tables - catalog_tables
        
        if not missing_tables:
            return {"synced": 0, "message": "All tables already synced"}
        
        # Register missing tables
        from ..database.database import get_db_connection
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        synced = 0
        for table_name in missing_tables:
            try:
                # Generate a placeholder entry for the table
                cursor.execute('''
                    INSERT INTO datasets (user_id, file_path, file_hash, table_name, file_size, source_mtime)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, file_hash) DO NOTHING
                ''', (user_id, f"[synced from DuckDB]", table_name, table_name, 0, 0))
                synced += 1
            except Exception:
                pass
        
        db_conn.commit()
        db_conn.close()
        
        return {"synced": synced, "message": f"Synced {synced} tables from DuckDB"}
    except Exception as e:
        return {"synced": 0, "message": f"Error: {str(e)}"}


@router.get("/list", response_model=List[DatasetInfo])
def list_user_datasets(current_user: dict = Depends(get_current_user)):
    """List all datasets for the current user (auto-syncs from DuckDB first)"""
    # Auto-sync before listing
    try:
        sync_duckdb_tables(current_user)
    except Exception:
        pass  # Continue even if sync fails
    
    user_id = current_user["user_id"]
    rows = list_datasets(user_id)
    results: List[DatasetInfo] = []
    for ds in rows:
        results.append(DatasetInfo(
            data_path=ds["file_path"],
            table_name=ds["table_name"],
            schema_path=ds.get("schema_path"),
            file_hash=ds["file_hash"],
            file_size=ds.get("file_size"),
            source_mtime=ds.get("source_mtime"),
            created_at=ds.get("created_at"),
            updated_at=ds.get("updated_at"),
        ))
    return results


class DatasetHealthResponse(BaseModel):
    table_name: str
    healthy: bool
    error: Optional[str] = None
    row_count: Optional[int] = None


@router.get("/health/{table_name}", response_model=DatasetHealthResponse)
def check_dataset_health(
    table_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Check health of a dataset by verifying DuckDB table integrity"""
    import duckdb
    from pathlib import Path
    from ..database.database import get_dataset_by_table_name
    
    user_id = current_user["user_id"]
    ds = get_dataset_by_table_name(user_id, table_name)
    
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{table_name}' not found")
    
    # Try to query the DuckDB table
    try:
        db_path = Path.home() / ".inquira" / user_id / f"{user_id}_data.duckdb"
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


class DatasetDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_files: List[str] = []


@router.delete("/{table_name}", response_model=DatasetDeleteResponse)
def delete_dataset_endpoint(
    table_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a dataset and its associated files (schema, cache, DuckDB table)"""
    import duckdb
    from pathlib import Path
    from ..database.database import get_dataset_by_table_name, delete_dataset
    
    user_id = current_user["user_id"]
    ds = get_dataset_by_table_name(user_id, table_name)
    
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{table_name}' not found")
    
    deleted_files = []
    
    # 1. Delete schema file if exists
    if ds.get("schema_path"):
        schema_path = Path(ds["schema_path"])
        if schema_path.exists():
            try:
                schema_path.unlink()
                deleted_files.append(str(schema_path))
            except Exception:
                pass
    
    # 2. Delete preview cache files
    cache_dir = Path.home() / ".inquira" / user_id / "schemas"
    for cache_file in cache_dir.glob(f"*_preview_*.pkl"):
        try:
            cache_file.unlink()
            deleted_files.append(str(cache_file))
        except Exception:
            pass
    
    # 3. Drop table from DuckDB
    db_path = Path.home() / ".inquira" / user_id / f"{user_id}_data.duckdb"
    if db_path.exists():
        try:
            conn = duckdb.connect(str(db_path))
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.close()
            deleted_files.append(f"DuckDB table: {table_name}")
        except Exception as e:
            # Log but continue - table might already be gone
            pass
    
    # 4. Delete from datasets catalog
    success = delete_dataset(user_id, table_name)
    
    if success:
        return DatasetDeleteResponse(
            success=True,
            message=f"Dataset '{table_name}' deleted successfully",
            deleted_files=deleted_files
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to delete dataset from catalog")
