import duckdb
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import os
from .auth import get_current_user
from ..database import get_user_settings

router = APIRouter(tags=["Data Preview"])

def get_file_type(file_path: str) -> str:
    """Determine file type based on extension"""
    if file_path.lower().endswith('.csv'):
        return 'csv'
    elif file_path.lower().endswith(('.xlsx', '.xls')):
        return 'excel'
    elif file_path.lower().endswith('.parquet'):
        return 'parquet'
    elif file_path.lower().endswith('.json'):
        return 'json'
    else:
        # Try to detect from content or default to CSV
        return 'csv'

def read_file_with_duckdb(file_path: str, sample_size: int = 100) -> List[Dict[str, Any]]:
    """
    Read a sample of data from various file formats using DuckDB
    """
    try:
        file_type = get_file_type(file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found: {file_path}"
            )

        # Connect to DuckDB
        con = duckdb.connect(database=':memory:')

        try:
            # Create table from file based on type
            if file_type == 'csv':
                # Read CSV with auto-detection
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_csv_auto('{file_path}')")
            elif file_type == 'excel':
                # For Excel, we'll use pandas first then import to DuckDB
                df = pd.read_excel(file_path)
                con.register('temp_df', df)
                con.execute("CREATE TABLE temp_table AS SELECT * FROM temp_df")
            elif file_type == 'parquet':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_parquet('{file_path}')")
            elif file_type == 'json':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_json_auto('{file_path}')")
            else:
                # Try CSV as fallback
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_csv_auto('{file_path}')")

            # Get sample data using DuckDB SAMPLE
            result = con.execute(f"SELECT * FROM temp_table USING SAMPLE {sample_size} ROWS").fetchall()

            # Get column names
            column_names = [desc[0] for desc in con.execute("DESCRIBE temp_table").fetchall()]

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

@router.get("/data/schema")
async def get_data_schema(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get schema information for the user's data file
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

        # Get schema information
        schema_info = get_file_schema(data_path)

        return {
            "success": True,
            "schema": schema_info,
            "file_path": data_path,
            "message": f"Successfully retrieved schema for {len(schema_info)} columns"
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
    sample_type: str = "random",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a preview of the user's data file with different sampling options

    Args:
        sample_type: Type of sampling - "random", "first", or "last"
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

        # Read sample data based on type
        sample_data = read_file_with_duckdb_sample(data_path, sample_type, 100)

        sample_type_text = {
            "random": "random",
            "first": "first",
            "last": "last"
        }.get(sample_type, "random")

        return {
            "success": True,
            "data": sample_data,
            "row_count": len(sample_data),
            "file_path": data_path,
            "sample_type": sample_type,
            "message": f"Successfully loaded {len(sample_data)} {sample_type_text} sample rows"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving data preview: {str(e)}"
        )

def get_file_schema(file_path: str) -> List[Dict[str, Any]]:
    """
    Get schema information (column names and types) from a file
    """
    try:
        file_type = get_file_type(file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found: {file_path}"
            )

        # Connect to DuckDB
        con = duckdb.connect(database=':memory:')

        try:
            # Create table from file based on type
            if file_type == 'csv':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_csv_auto('{file_path}')")
            elif file_type == 'excel':
                df = pd.read_excel(file_path)
                con.register('temp_df', df)
                con.execute("CREATE TABLE temp_table AS SELECT * FROM temp_df")
            elif file_type == 'parquet':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_parquet('{file_path}')")
            elif file_type == 'json':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_json_auto('{file_path}')")
            else:
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_csv_auto('{file_path}')")

            # Get column information
            columns_info = con.execute("DESCRIBE temp_table").fetchall()

            # Convert to schema format
            schema = []
            for col_info in columns_info:
                column_name = col_info[0]
                column_type = col_info[1]

                # Get sample values to infer more details
                try:
                    sample_values = con.execute(f"SELECT {column_name} FROM temp_table LIMIT 5").fetchall()
                    sample_value = sample_values[0][0] if sample_values else None
                except:
                    sample_value = None

                schema.append({
                    "name": column_name,
                    "type": column_type,
                    "nullable": True,  # DuckDB doesn't provide nullability info easily
                    "sample_value": str(sample_value) if sample_value is not None else None
                })

            return schema

        finally:
            con.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving schema: {str(e)}"
        )

def read_file_with_duckdb_sample(file_path: str, sample_type: str = "random", sample_size: int = 100) -> List[Dict[str, Any]]:
    """
    Read a sample of data from various file formats using DuckDB with different sampling methods
    """
    try:
        file_type = get_file_type(file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Data file not found: {file_path}"
            )

        # Connect to DuckDB
        con = duckdb.connect(database=':memory:')

        try:
            # Create table from file based on type
            if file_type == 'csv':
                # Read CSV with auto-detection
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_csv_auto('{file_path}')")
            elif file_type == 'excel':
                # For Excel, we'll use pandas first then import to DuckDB
                df = pd.read_excel(file_path)
                con.register('temp_df', df)
                con.execute("CREATE TABLE temp_table AS SELECT * FROM temp_df")
            elif file_type == 'parquet':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_parquet('{file_path}')")
            elif file_type == 'json':
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_json_auto('{file_path}')")
            else:
                # Try CSV as fallback
                con.execute(f"CREATE TABLE temp_table AS SELECT * FROM read_csv_auto('{file_path}')")

            # Get sample data based on type
            if sample_type == "random":
                result = con.execute(f"SELECT * FROM temp_table USING SAMPLE {sample_size} ROWS").fetchall()
            elif sample_type == "first":
                result = con.execute(f"SELECT * FROM temp_table LIMIT {sample_size}").fetchall()
            elif sample_type == "last":
                # Get total count first
                total_count = con.execute("SELECT COUNT(*) FROM temp_table").fetchone()[0]
                offset = max(0, total_count - sample_size)
                result = con.execute(f"SELECT * FROM temp_table LIMIT {sample_size} OFFSET {offset}").fetchall()
            else:
                # Default to random
                result = con.execute(f"SELECT * FROM temp_table USING SAMPLE {sample_size} ROWS").fetchall()

            # Get column names
            column_names = [desc[0] for desc in con.execute("DESCRIBE temp_table").fetchall()]

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