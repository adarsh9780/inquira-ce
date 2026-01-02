import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core.fingerprint import file_fingerprint_md5
from ..core.path_utils import (
    get_schema_path,
    get_legacy_schemas_dir,
    get_dataset_dir,
    SCHEMA_FILENAME
)

# Schema folder path - now using user-specific directories
# BASE_DIR and SCHEMAS_SUBDIR logic replaced by path_utils

class SchemaColumn:
    def __init__(self, name: str, description: str, data_type: str = "", sample_values: Optional[List[Any]] = None):
        self.name = name
        self.description = description
        self.data_type = data_type
        self.sample_values = sample_values or []

    def to_dict(self) -> Dict[str, Any]:
        def _serialize(val):
            if hasattr(val, 'isoformat'):
                return val.isoformat()
            if hasattr(val, '__str__') and not isinstance(val, (int, float, bool, type(None), list, dict)):
                # Convert other non-standard objects to string, but keep basic types
                return str(val)
            return val

        return {
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "sample_values": [_serialize(v) for v in self.sample_values]
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
    """Generate a per-file schema filename using a fingerprint of the data file (Legacy)"""
    fingerprint = file_fingerprint_md5(data_filepath)
    return f"{user_id}_{fingerprint}_schema.json"

def get_user_schema_dir(user_id: str) -> Path:
    """Get the schema directory for a specific user (Legacy)"""
    return get_legacy_schemas_dir(user_id)

def derive_table_name(filepath: str) -> str:
    """Derive table name from filepath (helper to avoid circular import)"""
    stem = Path(filepath).stem
    table_name = "".join(c if c.isalnum() else "_" for c in stem)
    if table_name and not table_name[0].isalpha():
        table_name = f"t_{table_name}"
    if not table_name:
        table_name = "data_table"
    return table_name.lower()

def save_schema(user_id: str, schema: SchemaFile, table_name: Optional[str] = None) -> str:
    """Save a schema to a JSON file.
    
    Args:
        user_id: user identifier
        schema: SchemaFile object
        table_name: Optional DuckDB table name. If not provided, derived from schema.filepath.
    
    Returns:
        Absolute path to the saved schema file.
    """
    if not table_name:
        table_name = derive_table_name(schema.filepath)
        
    # 1. New Structure: ~/.inquira/{username}/{table_name}/schema.json
    try:
        schema_path = get_schema_path(user_id, table_name)
    except Exception:
        # Fallback if user lookup fails (unlikely in normal flow)
        schema_path = None

    # Update timestamps and enrich with file metadata for freshness checks
    schema.updated_at = datetime.now().isoformat()
    try:
        p = Path(schema.filepath)
        if p.exists():
            st = p.stat()
            extra = {
                "file_fingerprint": file_fingerprint_md5(schema.filepath),
                "source_mtime": getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)),
                "file_size": st.st_size,
            }
        else:
            extra = {}
    except Exception:
        extra = {}

    data = schema.to_dict()
    data.update(extra)

    if schema_path:
        # New way
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        with open(schema_path, 'w') as f:
            json.dump(data, f, indent=2)
        return str(schema_path)
    else:
        # Old way fallback
        schema_dir = get_legacy_schemas_dir(user_id)
        schema_dir.mkdir(parents=True, exist_ok=True)
        filename = get_schema_filename(user_id, schema.filepath)
        filepath = schema_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return str(filepath)

def load_schema(user_id: str, data_filepath: str, table_name: Optional[str] = None) -> Optional[SchemaFile]:
    """Load a schema for a specific data file.

    Args:
        user_id: user identifier
        data_filepath: source file path (used for verification/freshness check)
        table_name: Optional. If validation against new structure is desired.
    """
    if not table_name:
        table_name = derive_table_name(data_filepath)

    # 1. Try New Structure
    try:
        schema_path = get_schema_path(user_id, table_name, create=False)
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                data = json.load(f)
            
            # Freshness check
            if _is_schema_fresh(data, data_filepath):
                return SchemaFile.from_dict(data)
            else:
                return None
    except Exception:
        # Fallback to legacy if user lookup fails or path issues
        pass

    # 2. Try Legacy Structure
    try:
        schema_dir = get_legacy_schemas_dir(user_id)
        filename = get_schema_filename(user_id, data_filepath)
        filepath = schema_dir / filename

        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)

            if _is_schema_fresh(data, data_filepath):
                return SchemaFile.from_dict(data)
    except Exception:
        pass

    return None

def _is_schema_fresh(data: Dict, data_filepath: str) -> bool:
    """Helper to check if cached schema matches current file version"""
    try:
        p = Path(data_filepath)
        if not p.exists():
            return True # If source file missing, assume schema is valid (or irrelevant)
            
        st = p.stat()
        saved_mtime = data.get("source_mtime")
        saved_size = data.get("file_size")
        if saved_mtime is not None and saved_size is not None:
            current_mtime = getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))
            current_size = st.st_size
            if int(saved_mtime) != int(current_mtime) or int(saved_size) != int(current_size):
                return False
    except Exception:
        pass # verification failed
    return True

def list_user_schemas(user_id: str) -> List[Dict[str, Any]]:
    """List all schemas for a user (scans legacy and new)"""
    schemas: List[Dict[str, Any]] = []

    # New Structure Scan
    from ..core.path_utils import list_dataset_dirs
    try:
        dataset_dirs = list_dataset_dirs(user_id)
        for d in dataset_dirs:
            s_path = d / SCHEMA_FILENAME
            if s_path.exists():
                try:
                    with open(s_path, 'r') as f:
                        data = json.load(f)
                    schemas.append({
                        "filename": d.name, # Use folder name as identifier
                        "filepath": data.get("filepath", ""),
                        "context": data.get("context", ""),
                        "columns_count": len(data.get("columns", [])),
                        "updated_at": data.get("updated_at", "")
                    })
                except Exception:
                    continue
    except Exception:
        pass

    # Legacy structure scan omitted if we found items, or merge?
    # Simple strategy: If we have schemas from new structure, prefer them.
    # Otherwise check legacy.
    
    if not schemas:
        try:
            schema_dir = get_legacy_schemas_dir(user_id)
            if schema_dir.exists():
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
                    except Exception:
                        continue
        except Exception:
            pass

    return schemas

def delete_schema(user_id: str, data_filepath: str, table_name: Optional[str] = None) -> bool:
    """Delete a schema file for the specific data file"""
    deleted = False
    
    if not table_name:
        table_name = derive_table_name(data_filepath)
        
    # 1. New Structure
    try:
        schema_path = get_schema_path(user_id, table_name, create=False)
        if schema_path.exists():
            schema_path.unlink()
            deleted = True
    except Exception:
        pass

    # 2. Legacy Structure
    if not deleted:
        try:
            schema_dir = get_legacy_schemas_dir(user_id)
            filename = get_schema_filename(user_id, data_filepath)
            filepath = schema_dir / filename

            if filepath.exists():
                filepath.unlink()
                deleted = True
        except Exception:
            pass
            
    return deleted
