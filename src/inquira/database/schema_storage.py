import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core.fingerprint import file_fingerprint_md5

# Schema folder path - now using user-specific directories
BASE_DIR = Path.home() / ".inquira"
SCHEMAS_SUBDIR = "schemas"

class SchemaColumn:
    def __init__(self, name: str, description: str, data_type: str = "", sample_values: Optional[List[Any]] = None):
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
    def __init__(self, filepath: str, context: str, columns: List[SchemaColumn], created_at: Optional[str] = None, updated_at: Optional[str] = None):
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
            created_at=data.get("created_at") or None,
            updated_at=data.get("updated_at") or None
        )

def get_schema_filename(user_id: str, data_filepath: str) -> str:
    """Generate a per-file schema filename using a fingerprint of the data file"""
    fingerprint = file_fingerprint_md5(data_filepath)
    return f"{user_id}_{fingerprint}_schema.json"

def get_user_schema_dir(user_id: str) -> Path:
    """Get the schema directory for a specific user"""
    user_dir = BASE_DIR / user_id / SCHEMAS_SUBDIR
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def save_schema(user_id: str, schema: SchemaFile) -> str:
    """Save a schema to a JSON file (per-file fingerprint)"""
    schema_dir = get_user_schema_dir(user_id)
    filename = get_schema_filename(user_id, schema.filepath)
    filepath = schema_dir / filename

    # Update timestamps and enrich with file metadata for freshness checks
    schema.updated_at = datetime.now().isoformat()
    try:
        p = Path(schema.filepath)
        st = p.stat()
        extra = {
            "file_fingerprint": file_fingerprint_md5(schema.filepath),
            "source_mtime": getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)),
            "file_size": st.st_size,
        }
    except Exception:
        extra = {}

    data = schema.to_dict()
    data.update(extra)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    return str(filepath)

def load_schema(user_id: str, data_filepath: str) -> Optional[SchemaFile]:
    """Load a schema for a specific data file.

    Uses per-file fingerprinted filenames only. Performs freshness check against
    current file mtime/size when metadata exists. No legacy fallback.
    """
    schema_dir = get_user_schema_dir(user_id)
    filename = get_schema_filename(user_id, data_filepath)
    filepath = schema_dir / filename

    # Try hashed schema first
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Freshness check using metadata if present
            try:
                p = Path(data_filepath)
                st = p.stat()
                saved_mtime = data.get("source_mtime")
                saved_size = data.get("file_size")
                if saved_mtime is not None and saved_size is not None:
                    current_mtime = getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))
                    current_size = st.st_size
                    if int(saved_mtime) != int(current_mtime) or int(saved_size) != int(current_size):
                        return None
            except Exception:
                # If we cannot verify, assume usable
                pass

            return SchemaFile.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    return None

def list_user_schemas(user_id: str) -> List[Dict[str, Any]]:
    """List all schemas for a user"""
    schema_dir = get_user_schema_dir(user_id)
    schemas: List[Dict[str, Any]] = []

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
    """Delete a schema file for the specific data file"""
    schema_dir = get_user_schema_dir(user_id)
    filename = get_schema_filename(user_id, data_filepath)
    filepath = schema_dir / filename

    if filepath.exists():
        filepath.unlink()
        return True
    return False
