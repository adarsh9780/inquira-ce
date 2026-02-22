"""
data_inspect.py — Quick file header inspection

Returns column names and row count by reading just the first few rows.
No DuckDB conversion, no background processing — just a fast sync read.
"""

from pathlib import Path

import duckdb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["data"])


class InspectRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path to the data file")


class InspectResponse(BaseModel):
    table_name: str
    columns: list[dict]
    row_count: int
    file_path: str


def _derive_table_name(file_path: str) -> str:
    stem = Path(file_path).stem
    name = "".join(c if c.isalnum() else "_" for c in stem)
    if name and not name[0].isalpha():
        name = f"t_{name}"
    return (name or "data_table").lower()


@router.post("/data/inspect", response_model=InspectResponse)
async def inspect_file(request: InspectRequest):
    """Read file header and return columns + row count without full conversion."""
    fp = Path(request.file_path)
    if not fp.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {request.file_path}")

    suffix = fp.suffix.lower()
    table_name = _derive_table_name(request.file_path)

    try:
        # Use an in-memory DuckDB just to sniff the schema
        conn = duckdb.connect(":memory:")

        if suffix == ".csv":
            conn.execute(f"CREATE TABLE data AS SELECT * FROM read_csv_auto('{request.file_path}', sample_size=100)")
        elif suffix == ".tsv":
            conn.execute(f"CREATE TABLE data AS SELECT * FROM read_csv_auto('{request.file_path}', delim='\\t', sample_size=100)")
        elif suffix in (".parquet", ".pq"):
            conn.execute(f"CREATE TABLE data AS SELECT * FROM read_parquet('{request.file_path}')")
        elif suffix in (".json", ".jsonl", ".ndjson"):
            conn.execute(f"CREATE TABLE data AS SELECT * FROM read_json_auto('{request.file_path}', sample_size=100)")
        elif suffix in (".xlsx", ".xls"):
            # DuckDB can read Excel via spatial extension, but it needs installing
            try:
                conn.execute("INSTALL spatial; LOAD spatial;")
                conn.execute(f"CREATE TABLE data AS SELECT * FROM st_read('{request.file_path}')")
            except Exception:
                raise HTTPException(status_code=400, detail="Excel support requires the DuckDB spatial extension")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        # Get columns
        col_info = conn.execute("DESCRIBE data").fetchall()
        columns = [{"name": row[0], "type": row[1]} for row in col_info]

        # Get row count
        row_count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

        conn.close()

        return InspectResponse(
            table_name=table_name,
            columns=columns,
            row_count=row_count,
            file_path=request.file_path,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect file: {str(e)}")
