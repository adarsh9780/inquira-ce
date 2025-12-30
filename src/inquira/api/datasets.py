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


@router.get("/list", response_model=List[DatasetInfo])
def list_user_datasets(current_user: dict = Depends(get_current_user)):
    """List all datasets for the current user"""
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

