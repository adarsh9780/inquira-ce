from typing import Any, List, Optional

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from ..services.llm_service import LLMService
from ..core.config_models import AppConfig
from ..database.database_manager import DatabaseManager

from ..database.database import (
    get_dataset_by_path,
    get_user_settings,
    save_user_settings,
    set_dataset_schema_path,
)
from ..core.prompt_library import get_prompt
from ..database.schema_storage import SchemaColumn, SchemaFile, load_schema, save_schema
from .auth import get_current_user
from ..core.logger import logprint


def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state


def get_api_key(current_user: dict = Depends(get_current_user)):
    """Dependency to get API key from user settings or environment"""
    user_id = current_user["user_id"]
    logprint(f"🔍 [API Key] Retrieving API key for user: {user_id}")

    user_settings = get_user_settings(user_id)
    logprint(f"🔍 [API Key] User settings retrieved: {user_settings}")

    api_key = user_settings.get("api_key")
    logprint(
        f"🔍 [API Key] API key from settings: {'***' + api_key[-4:] if api_key else 'None'}"
    )

    if not api_key:
        # Check environment variable as fallback
        import os

        api_key = os.getenv("GOOGLE_API_KEY", "")
        logprint(
            f"🔍 [API Key] API key from environment: {'***' + api_key[-4:] if api_key else 'None'}"
        )

    logprint(
        f"🔍 [API Key] Final API key status: {'Available' if api_key else 'Not available'}"
    )
    return api_key


router = APIRouter(prefix="/schemas", tags=["Schemas"])


class GenerateSchemaRequest(BaseModel):
    filepath: str = Field(description="filepath where the data is stored")
    context: Optional[str] = Field(None, description="optional context override")
    force_regenerate: bool = Field(False, description="Force regeneration even if schema exists")


class Column(BaseModel):
    name: str
    dtype: str
    samples: list[Any]


class Schema(BaseModel):
    name: str
    description: str


class SchemaList(BaseModel):
    schemas: List[Schema]


class SchemaColumnResponse(BaseModel):
    name: str
    description: str
    data_type: str
    sample_values: List[Any]


class SchemaResponse(BaseModel):
    filepath: str
    context: str
    columns: List[SchemaColumnResponse]
    created_at: str
    updated_at: str


class SaveSchemaRequest(BaseModel):
    filepath: str
    context: str
    columns: List[SchemaColumnResponse]


def _generate_schema_internal(
    user_id: str,
    filepath: str,
    context: str,
    api_key: str,
    app_state,
    model: str = "gemini-2.5-flash",
    force_regenerate: bool = False,
) -> SchemaResponse:
    # First, check if schema already exists (skip if force_regenerate is True)
    if not force_regenerate:
        existing_schema = load_schema(user_id, filepath)
        if existing_schema:
            return SchemaResponse(
                filepath=existing_schema.filepath,
                context=existing_schema.context,
                columns=[
                    SchemaColumnResponse(
                        name=col.name,
                        description=col.description,
                        data_type=col.data_type,
                        sample_values=col.sample_values,
                    )
                    for col in existing_schema.columns
                ],
                created_at=existing_schema.created_at,
                updated_at=existing_schema.updated_at,
            )

    user_settings = get_user_settings(user_id)
    context = context or user_settings.get("context", "General data analysis")
    logprint(f"🔑 [Schema] API key available: {'Yes' if api_key else 'No'}")
    logprint(f"📝 [Schema] Context: {context}")

    # Check if API key is available before proceeding
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key not set. Please set your API key in settings or environment variables.",
        )

    # Initialize LLM service with the user's API key
    try:
        llm_service = LLMService(api_key=api_key)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service not available. Please check your API key: {str(e)}",
        )

    # Check for cached DuckDB connection first
    connection_key = f"{user_id}:{filepath}"
    cached_connection = None

    if (
        hasattr(app_state, "duckdb_connections")
        and connection_key in app_state.duckdb_connections
    ):
        cached_connection = app_state.duckdb_connections[connection_key]
        logprint(f"✅ [Schema] Using cached DuckDB connection for: {connection_key}")
    elif (
        hasattr(app_state, "duckdb_connections")
        and "current_user" in app_state.duckdb_connections
    ):
        # Fallback for frontend using "current_user"
        cached_connection = app_state.duckdb_connections["current_user"]
        logprint("⚠️ [Schema] Using 'current_user' cached connection (frontend issue)")

    # Resolve the actual table name for this file
    table_name = None
    try:
        ds = get_dataset_by_path(user_id, filepath)
        if ds and ds.get("table_name"):
            table_name = ds["table_name"]
    except Exception:
        table_name = None

    if not table_name:
        try:
            cfg = (
                app_state.config
                if hasattr(app_state, "config") and app_state.config
                else AppConfig()
            )
            dm = DatabaseManager(cfg)
            table_name = dm._get_table_name(filepath)
        except Exception:
            table_name = "data_table"

    if cached_connection:
        # Use cached connection
        try:
            # Test the connection by selecting from the resolved table
            test_result = cached_connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            logprint(
                f"✅ [Schema] Cached connection test successful, rows: {test_result[0]}"
            )

            description = cached_connection.execute(f"DESCRIBE {table_name}").fetchall()
            columns = []
            for row in description:
                column_name = row[0]
                column_type = row[1]

                samples = cached_connection.execute(
                    f'SELECT DISTINCT "{column_name}" FROM {table_name} LIMIT 10'
                ).fetchall()
                samples = [s[0] for s in samples]

                c = Column(name=column_name, dtype=column_type, samples=samples)
                columns.append(c)

        except Exception as e:
            logprint(f"❌ [Schema] Error using cached connection: {str(e)}", level="error")
            raise HTTPException(
                status_code=500, detail=f"Error accessing cached database: {str(e)}"
            )
    else:
        description = duckdb.sql(f'describe "{filepath}"').fetchall()
        columns = []
        for row in description:
            column_name = row[0]
            column_type = row[1]

            samples = duckdb.sql(
                f"select distinct \"{column_name}\" from '{filepath}' limit 10"
            ).fetchall()
            samples = [s[0] for s in samples]

            c = Column(name=column_name, dtype=column_type, samples=samples)
            columns.append(c)

    # Format columns for the prompt
    columns_text = "\n".join(
        [
            f"- {col.name} ({col.dtype}): {col.samples[:3]}"  # Show first 3 samples
            for col in columns
        ]
    )

    prompt = get_prompt("schema_generation", context=context, columns_text=columns_text)

    # Use the LLM service to generate schema descriptions
    schema_response = llm_service.ask(
        user_query=prompt,
        structured_output_format=SchemaList,
    )

    # Convert to SchemaColumn objects and save
    schema_columns = []
    schemas_list = (
        schema_response.schemas
        if hasattr(schema_response, "schemas")
        else (schema_response if isinstance(schema_response, list) else [])
    )
    for schema_item in schemas_list:
        # Find matching column for data type and samples
        matching_column = next(
            (col for col in columns if col.name == schema_item.name), None
        )
        if matching_column:
            schema_col = SchemaColumn(
                name=schema_item.name,
                description=schema_item.description,
                data_type=matching_column.dtype,
                sample_values=matching_column.samples,
            )
            schema_columns.append(schema_col)

    # Save the generated schema
    schema_file = SchemaFile(filepath=filepath, context=context, columns=schema_columns)
    saved_schema_path = save_schema(user_id, schema_file)

    # Persist schema path in datasets catalog
    try:
        set_dataset_schema_path(user_id, filepath, saved_schema_path)
    except Exception as e:
        logprint(f"⚠️ [Schema] Failed to update dataset schema_path: {e}", level="warning")

    # Update user settings with the schema path
    current_settings = get_user_settings(user_id)
    current_settings["schema_path"] = saved_schema_path
    save_user_settings(user_id, current_settings)

    # Update app_state with the schema path
    app_state.schema_path = saved_schema_path

    # Return the response
    return SchemaResponse(
        filepath=filepath,
        context=context,
        columns=[
            SchemaColumnResponse(
                name=col.name,
                description=col.description,
                data_type=col.data_type,
                sample_values=col.sample_values,
            )
            for col in schema_columns
        ],
        created_at=schema_file.created_at,
        updated_at=schema_file.updated_at,
    )


@router.post("/generate")
def generate_schema(
    request: GenerateSchemaRequest,
    current_user: dict = Depends(get_current_user),
    current_api_key: str = Depends(get_api_key),
    app_state=Depends(get_app_state),
    model: str = "gemini-2.5-flash",
):
    user_id = current_user["user_id"]
    logprint(f"🔄 [Schema] Generate request for {request.filepath}, force={request.force_regenerate}")
    return _generate_schema_internal(
        user_id=user_id,
        filepath=request.filepath,
        context=request.context,
        api_key=current_api_key,
        app_state=app_state,
        model=model,
        force_regenerate=request.force_regenerate,
    )


@router.get("/load/{filepath:path}")
def load_schema_endpoint(
    filepath: str,
    current_user: dict = Depends(get_current_user),
    app_state=Depends(get_app_state),
):
    """Load an existing schema for a data file.

    If no schema exists yet, attempt to generate a minimal schema (without LLM)
    based on DuckDB DESCRIBE and sample values, then save and return it.
    """
    user_id = current_user["user_id"]
    existing = load_schema(user_id, filepath)

    if existing:
        return SchemaResponse(
            filepath=existing.filepath,
            context=existing.context,
            columns=[
                SchemaColumnResponse(
                    name=col.name,
                    description=col.description,
                    data_type=col.data_type,
                    sample_values=col.sample_values,
                )
                for col in existing.columns
            ],
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )

    # Minimal auto-generation without LLM as a fallback
    try:
        # Prefer using cached DuckDB connection if available
        connection = None
        if hasattr(app_state, "duckdb_connections"):
            key = f"{user_id}:{filepath}"
            connection = app_state.duckdb_connections.get(
                key
            ) or app_state.duckdb_connections.get("current_user")

        columns: list[Column] = []
        if connection is not None:
            # Resolve table name similarly to generate_schema
            try:
                ds = get_dataset_by_path(user_id, filepath)
                tbl = ds["table_name"] if ds and ds.get("table_name") else "data_table"
            except Exception:
                tbl = "data_table"

            desc = connection.execute(f"DESCRIBE {tbl}").fetchall()
            for row in desc:
                col_name = row[0]
                col_type = row[1]
                sample_rows = connection.execute(
                    f'SELECT DISTINCT "{col_name}" FROM {tbl} LIMIT 10'
                ).fetchall()
                sample_values = [s[0] for s in sample_rows]
                columns.append(
                    Column(name=col_name, dtype=col_type, samples=sample_values)
                )
        else:
            # File-based describe/sample
            desc = duckdb.sql(f'describe "{filepath}"').fetchall()
            for row in desc:
                col_name = row[0]
                col_type = row[1]
                sample_rows = duckdb.sql(
                    f"select distinct \"{col_name}\" from '{filepath}' limit 10"
                ).fetchall()
                sample_values = [s[0] for s in sample_rows]
                columns.append(
                    Column(name=col_name, dtype=col_type, samples=sample_values)
                )

        # Build minimal SchemaFile with generic context
        schema_columns = [
            SchemaColumn(
                name=c.name,
                description="",  # Minimal fallback without LLM
                data_type=c.dtype,
                sample_values=c.samples,
            )
            for c in columns
        ]

        schema_file = SchemaFile(
            filepath=filepath, context="General data analysis", columns=schema_columns
        )
        saved_path = save_schema(user_id, schema_file)

        # Persist schema path in datasets catalog
        try:
            from ..database.database import set_dataset_schema_path

            set_dataset_schema_path(user_id, filepath, saved_path)
        except Exception:
            pass

        return SchemaResponse(
            filepath=filepath,
            context=schema_file.context,
            columns=[
                SchemaColumnResponse(
                    name=col.name,
                    description=col.description,
                    data_type=col.data_type,
                    sample_values=col.sample_values,
                )
                for col in schema_columns
            ],
            created_at=schema_file.created_at,
            updated_at=schema_file.updated_at,
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Schema not found")


@router.post("/save")
def save_schema_endpoint(
    request: SaveSchemaRequest,
    current_user: dict = Depends(get_current_user),
    app_state=Depends(get_app_state),
):
    """Save a user-modified schema"""
    user_id = current_user["user_id"]

    # Convert request columns to SchemaColumn objects
    schema_columns = [
        SchemaColumn(
            name=col.name,
            description=col.description,
            data_type=col.data_type,
            sample_values=col.sample_values,
        )
        for col in request.columns
    ]

    # Create and save schema
    schema_file = SchemaFile(
        filepath=request.filepath, context=request.context, columns=schema_columns
    )

    saved_path = save_schema(user_id, schema_file)

    # Update user settings with the schema path
    current_settings = get_user_settings(user_id)
    current_settings["schema_path"] = saved_path
    save_user_settings(user_id, current_settings)

    # Update app_state with the schema path
    app_state.schema_path = saved_path

    return {
        "message": "Schema saved successfully",
        "filepath": saved_path,
        "updated_at": schema_file.updated_at,
    }


@router.get("/list")
def list_schemas_endpoint(current_user: dict = Depends(get_current_user)):
    """List all schemas for the current user"""
    from ..database.schema_storage import list_user_schemas

    user_id = current_user["user_id"]
    return list_user_schemas(user_id)
