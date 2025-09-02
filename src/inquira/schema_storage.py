import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from .auth import get_current_user
from fastapi import HTTPException, Depends

# Schema folder path
SCHEMA_DIR = Path.home() / ".inquira" / "schemas"

class SchemaColumn:
    def __init__(self, name: str, description: str, data_type: str = "", sample_values: List[Any] = None):
        self.name = name
        self.description = description
        self.data_type = data_type
        self.sample_values = sample_values or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "sample_values": self.sample_values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaColumn':
        return cls(
            name=data["name"],
            description=data["description"],
            data_type=data.get("data_type", ""),
            sample_values=data.get("sample_values", [])
        )

class SchemaFile:
    def __init__(self, filepath: str, context: str, columns: List[SchemaColumn], created_at: str = None, updated_at: str = None):
        self.filepath = filepath
        self.context = context
        self.columns = columns
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "context": self.context,
            "columns": [col.to_dict() for col in self.columns],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaFile':
        columns = [SchemaColumn.from_dict(col) for col in data["columns"]]
        return cls(
            filepath=data["filepath"],
            context=data["context"],
            columns=columns,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

def get_schema_filename(filepath: str) -> str:
    """Generate a filename for the schema based on the data file path"""
    # Create a safe filename from the filepath
    import hashlib
    file_hash = hashlib.md5(filepath.encode()).hexdigest()[:8]
    return f"schema_{file_hash}.json"

def get_user_schema_dir(user_id: str) -> Path:
    """Get the schema directory for a specific user"""
    user_dir = SCHEMA_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def save_schema(user_id: str, schema: SchemaFile) -> str:
    """Save a schema to a JSON file"""
    schema_dir = get_user_schema_dir(user_id)
    filename = get_schema_filename(schema.filepath)
    filepath = schema_dir / filename

    # Update the updated_at timestamp
    schema.updated_at = datetime.now().isoformat()

    with open(filepath, 'w') as f:
        json.dump(schema.to_dict(), f, indent=2)

    return str(filepath)

def load_schema(user_id: str, data_filepath: str) -> Optional[SchemaFile]:
    """Load a schema from a JSON file"""
    schema_dir = get_user_schema_dir(user_id)
    filename = get_schema_filename(data_filepath)
    filepath = schema_dir / filename

    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return SchemaFile.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None

def list_user_schemas(user_id: str) -> List[Dict[str, Any]]:
    """List all schemas for a user"""
    schema_dir = get_user_schema_dir(user_id)
    schemas = []

    if not schema_dir.exists():
        return schemas

    for file_path in schema_dir.glob("*.json"):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            schemas.append({
                "filename": file_path.name,
                "filepath": data.get("filepath", ""),
                "context": data.get("context", ""),
                "columns_count": len(data.get("columns", [])),
                "updated_at": data.get("updated_at", "")
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return schemas

def delete_schema(user_id: str, data_filepath: str) -> bool:
    """Delete a schema file"""
    schema_dir = get_user_schema_dir(user_id)
    filename = get_schema_filename(data_filepath)
    filepath = schema_dir / filename

    if filepath.exists():
        filepath.unlink()
        return True
    return False