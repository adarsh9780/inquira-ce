from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Any, List, Optional
import duckdb
from duckdb import BinderException
from .auth import get_current_user
from ..database import get_user_settings, save_user_settings
from ..schema_storage import SchemaFile, SchemaColumn, save_schema, load_schema

def get_app_state(request: Request):
    """Dependency to get app state"""
    return request.app.state

def get_api_key(current_user: dict = Depends(get_current_user)):
    """Dependency to check if API key is set in user settings"""
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id)
    api_key = user_settings.get("api_key")

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key not set. Please set your API key in settings first."
        )
    return api_key

router = APIRouter(prefix="/schema", tags=['Schema'])


class GenerateSchemaRequest(BaseModel):
    filepath: str = Field(description="filepath where the data is stored")
    context: Optional[str] = Field(None, description="optional context override")


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


@router.post("/generate")
def generate_schema(
    request: GenerateSchemaRequest,
    current_user: dict = Depends(get_current_user),
    current_api_key: str = Depends(get_api_key),
    app_state = Depends(get_app_state),
    model: str = "gemini-2.5-flash"
  ):
    # Get context from settings or use provided override
    user_id = current_user["user_id"]
    user_settings = get_user_settings(user_id)
    context = request.context or user_settings.get("context", "General data analysis")

    # Initialize LLM service with the user's API key
    try:
        from ..llm_service import LLMService
        llm_service = LLMService(api_key=current_api_key)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service not available. Please check your API key: {str(e)}"
        )

    try:
        duckdb.sql(f"select * from '{request.filepath}' limit 10;")
    except BinderException:
        raise HTTPException(
            status_code=400,
            detail="invalid file type, supported: json, parquet, or csv",
        )
    else:
        description = duckdb.sql(f'describe "{request.filepath}"').fetchall()
        columns = []
        for row in description:
            column_name = row[0]
            column_type = row[1]

            samples = duckdb.sql(
                f"select distinct {column_name} from '{request.filepath}' limit 10"
            ).fetchall()
            samples = [s[0] for s in samples]

            c = Column(name=column_name, dtype=column_type, samples=samples)
            columns.append(c)

        # Format columns for the prompt
        columns_text = "\n".join([
            f"- {col.name} ({col.dtype}): {col.samples[:3]}"  # Show first 3 samples
            for col in columns
        ])

        prompt = f"""
        You will be provided a list of columns, their data types and some sample values along with
        a little context. Your task is to generate the schema information based on the provided information.

        Context: {context}

        Columns:
        {columns_text}

        Please generate a schema description for each column that explains what this column represents
        in the context of the provided domain knowledge.
        """

        # Use the LLM service to generate schema descriptions
        schema_response = llm_service.ask(
            user_query=prompt,
            structured_output_format=SchemaList,
        )

        # Convert to SchemaColumn objects and save
        schema_columns = []
        schemas_list = schema_response.schemas if hasattr(schema_response, 'schemas') else (schema_response if isinstance(schema_response, list) else [])
        for schema_item in schemas_list:
            # Find matching column for data type and samples
            matching_column = next((col for col in columns if col.name == schema_item.name), None)
            if matching_column:
                schema_col = SchemaColumn(
                    name=schema_item.name,
                    description=schema_item.description,
                    data_type=matching_column.dtype,
                    sample_values=matching_column.samples
                )
                schema_columns.append(schema_col)

        # Save the generated schema
        schema_file = SchemaFile(
            filepath=request.filepath,
            context=context,
            columns=schema_columns
        )
        saved_schema_path = save_schema(user_id, schema_file)

        # Update user settings with the schema path
        current_settings = get_user_settings(user_id)
        current_settings['schema_path'] = saved_schema_path
        save_user_settings(user_id, current_settings)

        # Update app_state with the schema path
        app_state.schema_path = saved_schema_path

        # Return the response
        return SchemaResponse(
            filepath=request.filepath,
            context=context,
            columns=[
                SchemaColumnResponse(
                    name=col.name,
                    description=col.description,
                    data_type=col.data_type,
                    sample_values=col.sample_values
                ) for col in schema_columns
            ],
            created_at=schema_file.created_at,
            updated_at=schema_file.updated_at
        )

@router.get("/load/{filepath:path}")
def load_schema_endpoint(
    filepath: str,
    current_user: dict = Depends(get_current_user)
):
    """Load an existing schema for a data file"""
    user_id = current_user["user_id"]
    schema_file = load_schema(user_id, filepath)

    if not schema_file:
        raise HTTPException(status_code=404, detail="Schema not found")

    return SchemaResponse(
        filepath=schema_file.filepath,
        context=schema_file.context,
        columns=[
            SchemaColumnResponse(
                name=col.name,
                description=col.description,
                data_type=col.data_type,
                sample_values=col.sample_values
            ) for col in schema_file.columns
        ],
        created_at=schema_file.created_at,
        updated_at=schema_file.updated_at
    )

@router.post("/save")
def save_schema_endpoint(
    request: SaveSchemaRequest,
    current_user: dict = Depends(get_current_user),
    app_state = Depends(get_app_state)
):
    """Save a user-modified schema"""
    user_id = current_user["user_id"]

    # Convert request columns to SchemaColumn objects
    schema_columns = [
        SchemaColumn(
            name=col.name,
            description=col.description,
            data_type=col.data_type,
            sample_values=col.sample_values
        ) for col in request.columns
    ]

    # Create and save schema
    schema_file = SchemaFile(
        filepath=request.filepath,
        context=request.context,
        columns=schema_columns
    )

    saved_path = save_schema(user_id, schema_file)

    # Update user settings with the schema path
    current_settings = get_user_settings(user_id)
    current_settings['schema_path'] = saved_path
    save_user_settings(user_id, current_settings)

    # Update app_state with the schema path
    app_state.schema_path = saved_path

    return {
        "message": "Schema saved successfully",
        "filepath": saved_path,
        "updated_at": schema_file.updated_at
    }

@router.get("/list")
def list_schemas_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """List all schemas for the current user"""
    from ..schema_storage import list_user_schemas
    user_id = current_user["user_id"]
    return list_user_schemas(user_id)