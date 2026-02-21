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
from ..database.schema_storage import (
    SchemaColumn,
    SchemaFile,
    load_schema,
    save_schema,
    derive_table_name,
)
from .auth import get_current_user
from ..core.logger import logprint


def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state


def get_api_key(current_user: dict = Depends(get_current_user)):
    """Dependency to get API key from user settings or environment"""
    user_id = current_user["user_id"]
    logprint(f"🔍 [API Key] Retrieving API key for user: {user_id}", level="debug")

    user_settings = get_user_settings(user_id)
    logprint(f"🔍 [API Key] User settings retrieved: {user_settings}", level="debug")

    api_key = user_settings.get("api_key")
    logprint(
        f"🔍 [API Key] API key from settings: {'***' + api_key[-4:] if api_key else 'None'}",
        level="debug",
    )

    if not api_key:
        # Check environment variable as fallback
        import os

        api_key = os.getenv("GOOGLE_API_KEY", "")
        logprint(
            f"🔍 [API Key] API key from environment: {'***' + api_key[-4:] if api_key else 'None'}",
            level="debug",
        )

    logprint(
        f"🔍 [API Key] Final API key status: {'Available' if api_key else 'Not available'}",
        level="debug",
    )
    return api_key


router = APIRouter(prefix="/schemas", tags=["Schemas"])


class GenerateSchemaRequest(BaseModel):
    filepath: str = Field(description="filepath where the data is stored")
    context: Optional[str] = Field(None, description="optional context override")
    force_regenerate: bool = Field(
        False, description="Force regeneration even if schema exists"
    )


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
    context: str = ""  # Default to empty string if None
    columns: List[SchemaColumnResponse]
    created_at: str
    updated_at: str


class SaveSchemaRequest(BaseModel):
    filepath: str
    context: str
    columns: List[SchemaColumnResponse]


def _resolve_table_name(user_id: str, filepath: str, app_state) -> str:
    """Helper to resolve table name using catalog or derivation"""
    # 1. Try catalog
    try:
        ds = get_dataset_by_path(user_id, filepath)
        if ds and ds.get("table_name"):
            return ds["table_name"]
    except Exception:
        pass

    # 2. Try derivation helper
    try:
        return derive_table_name(filepath)
    except Exception:
        pass

    return "data_table"


def _generate_schema_internal(
    user_id: str,
    filepath: str,
    context: str,
    api_key: str,
    app_state,
    model: str = "gemini-2.5-flash",
    force_regenerate: bool = False,
) -> SchemaResponse:
    # Resolve table name early
    table_name = _resolve_table_name(user_id, filepath, app_state)

    # First, check if schema already exists (skip if force_regenerate is True)
    if not force_regenerate:
        # Pass table_name for efficient lookup
        existing_schema = load_schema(user_id, filepath, table_name=table_name)
        if existing_schema:
            return SchemaResponse(
                filepath=existing_schema.filepath,
                context=existing_schema.context or "",
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
    logprint(
        f"🔑 [Schema] API key available: {'Yes' if api_key else 'No'}", level="debug"
    )
    logprint(f"📝 [Schema] Context: {context}", level="debug")

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
        logprint(
            f"✅ [Schema] Using cached DuckDB connection for: {connection_key}",
            level="debug",
        )
    elif (
        hasattr(app_state, "duckdb_connections")
        and "current_user" in app_state.duckdb_connections
    ):
        # Fallback for frontend using "current_user"
        cached_connection = app_state.duckdb_connections["current_user"]
        logprint(
            "⚠️ [Schema] Using 'current_user' cached connection (frontend issue)",
            level="debug",
        )

    if cached_connection:
        # Use cached connection
        try:
            # Test the connection by selecting from the resolved table
            test_result = cached_connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            logprint(
                f"✅ [Schema] Cached connection test successful, rows: {test_result[0]}",
                level="debug",
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
            logprint(
                f"❌ [Schema] Error using cached connection: {str(e)}", level="error"
            )
            raise HTTPException(
                status_code=500, detail=f"Error accessing cached database: {str(e)}"
            )
    else:
        # Use explicit connection instead of duckdb.sql() to avoid race conditions
        # duckdb.sql() uses a shared in-memory connection that can have state issues
        try:
            conn = duckdb.connect()
            description = conn.execute(
                f'DESCRIBE SELECT * FROM "{filepath}"'
            ).fetchall()
            columns = []
            for row in description:
                column_name = row[0]
                column_type = row[1]

                samples = conn.execute(
                    f"SELECT DISTINCT \"{column_name}\" FROM '{filepath}' LIMIT 10"
                ).fetchall()
                samples = [s[0] for s in samples]

                c = Column(name=column_name, dtype=column_type, samples=samples)
                columns.append(c)
            conn.close()
        except Exception as e:
            logprint(f"❌ [Schema] DuckDB error reading file: {str(e)}", level="error")
            raise HTTPException(
                status_code=500, detail=f"Error reading data file: {str(e)}"
            )

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
    # Use table_name for saving to correct folder
    saved_schema_path = save_schema(user_id, schema_file, table_name=table_name)

    # Persist schema path in datasets catalog
    try:
        set_dataset_schema_path(user_id, filepath, saved_schema_path)
    except Exception as e:
        logprint(
            f"⚠️ [Schema] Failed to update dataset schema_path: {e}", level="warning"
        )

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
    logprint(
        f"🔄 [Schema] Generate request for {request.filepath}, force={request.force_regenerate}",
        level="debug",
    )
    return _generate_schema_internal(
        user_id=user_id,
        filepath=request.filepath,
        context=request.context,
        api_key=current_api_key,
        app_state=app_state,
        model=model,
        force_regenerate=request.force_regenerate,
    )


class ColumnInput(BaseModel):
    name: str
    dtype: str
    samples: List[Any] = Field(default_factory=list)


class GenerateFromColumnsRequest(BaseModel):
    """Request body for browser-native schema generation.
    The frontend sends column metadata directly from DuckDB-WASM
    instead of a file path the backend would read.
    """

    table_name: str = Field(description="DuckDB table name (e.g. 'ball_by_ball_ipl')")
    columns: List[ColumnInput] = Field(
        description="Columns with name, dtype, sample values"
    )
    context: Optional[str] = Field(None, description="User context for the LLM")


@router.post("/generate-from-columns")
def generate_schema_from_columns(
    request: GenerateFromColumnsRequest,
    current_user: dict = Depends(get_current_user),
    current_api_key: str = Depends(get_api_key),
    app_state=Depends(get_app_state),
):
    """Generate schema descriptions from column metadata sent by the frontend.

    This endpoint does NOT access any files — the frontend's DuckDB-WASM
    has already ingested the data and sends column info directly.
    The backend only runs the LLM to produce human-readable descriptions.
    """
    user_id = current_user["user_id"]
    table_name = request.table_name
    filepath = f"browser://{table_name}"  # Virtual path for storage
    logprint(
        f"🔄 [Schema] Generate-from-columns request: table={table_name}", level="debug"
    )

    # Check for existing schema
    existing = load_schema(user_id, filepath, table_name=table_name)
    if existing and existing.columns:
        has_descriptions = any(
            col.description.strip() for col in existing.columns if col.description
        )
        if has_descriptions:
            logprint(
                f"📋 [Schema] Returning existing schema for {table_name}", level="debug"
            )
            return SchemaResponse(
                filepath=existing.filepath,
                context=existing.context or "",
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

    # Validate API key
    if not current_api_key:
        raise HTTPException(
            status_code=400,
            detail="API key not set. Please set your API key in settings.",
        )

    # Initialize LLM
    try:
        llm_service = LLMService(api_key=current_api_key)
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"LLM service not available: {str(e)}"
        )

    # Get context
    user_settings = get_user_settings(user_id)
    context = request.context or user_settings.get("context", "General data analysis")

    # Build columns for prompt
    columns = [
        Column(name=c.name, dtype=c.dtype, samples=c.samples) for c in request.columns
    ]

    columns_text = "\n".join(
        [f"- {col.name} ({col.dtype}): {col.samples[:3]}" for col in columns]
    )

    prompt = get_prompt("schema_generation", context=context, columns_text=columns_text)

    # LLM generates descriptions
    schema_response = llm_service.ask(
        user_query=prompt, structured_output_format=SchemaList
    )

    # Merge LLM descriptions with column metadata
    schema_columns = []
    schemas_list = (
        schema_response.schemas
        if hasattr(schema_response, "schemas")
        else (schema_response if isinstance(schema_response, list) else [])
    )
    for schema_item in schemas_list:
        matching = next((c for c in columns if c.name == schema_item.name), None)
        if matching:
            schema_columns.append(
                SchemaColumn(
                    name=schema_item.name,
                    description=schema_item.description,
                    data_type=matching.dtype,
                    sample_values=matching.samples,
                )
            )

    # Save
    schema_file = SchemaFile(filepath=filepath, context=context, columns=schema_columns)
    saved_path = save_schema(user_id, schema_file, table_name=table_name)

    # Update user settings
    current_settings = get_user_settings(user_id)
    current_settings["schema_path"] = saved_path
    save_user_settings(user_id, current_settings)
    app_state.schema_path = saved_path

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
    # Normalize browser-native virtual paths from path params:
    # - "browser:/table" -> "browser://table"
    # - "/browser:/table" -> "browser://table"
    if filepath and filepath.startswith("/browser:/"):
        filepath = filepath[1:]
    if filepath and filepath.startswith("browser:/") and not filepath.startswith("browser://"):
        filepath = filepath.replace("browser:/", "browser://", 1)

    # Normalize filepath - FastAPI strips leading slash from path params
    # So "/Users/foo" becomes "Users/foo" - we need to restore it
    if filepath and not filepath.startswith("/") and not filepath.startswith("browser://"):
        filepath = "/" + filepath

    user_id = current_user["user_id"]
    table_name = _resolve_table_name(user_id, filepath, app_state)

    existing = load_schema(user_id, filepath, table_name=table_name)

    if existing:
        return SchemaResponse(
            filepath=existing.filepath,
            context=existing.context or "",
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

    # No schema exists - return 404
    # The schema will be generated when user clicks "Save Data Settings"
    # which triggers the proper background processing flow
    logprint(f"ℹ️ [Schema] No existing schema found for {filepath}", level="debug")
    raise HTTPException(
        status_code=404,
        detail="Schema not found. Save data settings to generate schema.",
    )


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

    table_name = _resolve_table_name(user_id, request.filepath, app_state)
    saved_path = save_schema(user_id, schema_file, table_name=table_name)

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
