import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import duckdb
import pandas as pd
from ..core.config_models import AppConfig
from .sql_library import get_sql
from .database import upsert_dataset, get_dataset_by_path
from ..core.fingerprint import file_fingerprint_md5
from ..core.logger import logprint
from ..core.path_utils import get_duckdb_cache_dir


class DatabaseManager:
    """
    Manages persistent DuckDB databases for efficient data access.
    Converts CSV files to DuckDB databases on first access and reuses them.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        # Use user's home directory for persistent storage
        from ..core.path_utils import BASE_DIR
        self.base_dir = BASE_DIR

        # In-memory connection cache: {db_path: connection}
        self.connections: Dict[str, duckdb.DuckDBPyConnection] = {}

        # Database metadata cache
        self.metadata_cache: Dict[str, dict] = {}

    def get_connection(self, user_id: str, file_path: str) -> duckdb.DuckDBPyConnection:
        """
        Get or create a database connection for the given file.
        Creates database file if it doesn't exist or is outdated.
        """
        db_path = self._get_database_path(user_id, file_path)

        # Check if database needs to be created/updated
        needs_recreation = self._should_recreate_database(user_id, db_path, file_path)
        if needs_recreation:
            logprint(
                f"🔧 [Database] Creating/updating database for user {user_id}: {file_path}"
            )
            self._create_database(user_id, db_path, file_path)
        else:
            logprint(
                f"♻️ [Database] Reusing existing database for user {user_id}: {file_path}"
            )

        # Get or create connection
        if str(db_path) not in self.connections:
            logprint(f"🔌 [Database] Creating new connection to: {db_path}")
            # Enforce memory cap and enable disk spilling for safety
            user_temp_dir = get_duckdb_cache_dir(user_id)
            self.connections[str(db_path)] = duckdb.connect(
                str(db_path),
                config={"memory_limit": "500MB", "temp_directory": str(user_temp_dir)},
            )
        else:
            logprint(f"🔗 [Database] Reusing existing connection to: {db_path}")

        # Update last accessed time
        self._update_last_accessed(db_path)

        return self.connections[str(db_path)]

    def get_existing_connection(
        self, user_id: str
    ) -> Optional[duckdb.DuckDBPyConnection]:
        """
        Get existing database connection for a user without creating new database.
        Returns None if database doesn't exist.
        """
        from ..core.path_utils import get_database_path
        db_path = get_database_path(user_id)

        if not db_path.exists():
            return None

        # Get or create connection
        if str(db_path) not in self.connections:
            # Enforce memory cap and enable disk spilling for safety
            user_temp_dir = get_duckdb_cache_dir(user_id)
            self.connections[str(db_path)] = duckdb.connect(
                str(db_path),
                config={"memory_limit": "500MB", "temp_directory": str(user_temp_dir)},
            )

        # Update last accessed time
        self._update_last_accessed(db_path)

        return self.connections[str(db_path)]

    def _get_database_path(self, user_id: str, file_path: str) -> Path:
        """Generate consistent database file path"""
        from ..core.path_utils import get_database_path
        return get_database_path(user_id)

    def _get_table_name(self, file_path: str) -> str:
        """Generate table name from file path"""
        # Use filename without extension, replace special chars with underscores
        filename = Path(file_path).stem
        # Replace any non-alphanumeric characters with underscores
        table_name = "".join(c if c.isalnum() else "_" for c in filename)
        # Ensure it starts with a letter
        if table_name and not table_name[0].isalpha():
            table_name = f"t_{table_name}"
        # Ensure it's not empty
        if not table_name:
            table_name = "data_table"
        return table_name.lower()

    def _should_recreate_database(self, user_id: str, db_path: Path, file_path: str) -> bool:
        """Check if DuckDB table needs to be created/updated using SQLite catalog and filesystem."""
        table_name = self._get_table_name(file_path)

        # Database doesn't exist
        if not db_path.exists():
            logprint(f"📁 [Database] Database doesn't exist, creating: {db_path}")
            return True

        # Source file must exist
        if not os.path.exists(file_path):
            logprint(
                f"❌ [Database] Source file doesn't exist: {file_path}", level="error"
            )
            return True

        # Consult datasets catalog for this file
        try:
            from .database import get_dataset_by_path
            # user_id is passed explicitly now
            dataset = get_dataset_by_path(user_id, file_path)
        except Exception:
            dataset = None

        if not dataset:
            logprint(f"📋 [Database] No dataset catalog entry found, creating table '{table_name}'")
            return True

        # Compare file modification time to cataloged source_mtime
        try:
            current_mtime = os.path.getmtime(file_path)
            stored_mtime = float(dataset.get('source_mtime') or 0)
        except Exception:
            current_mtime = 0
            stored_mtime = 0

        if current_mtime > stored_mtime:
            logprint(f"🔄 [Database] Source file updated since last ingest; recreating table '{table_name}'")
            return True

        # Also ensure the table actually exists in the DuckDB database
        try:
            conn = self.connections.get(str(db_path))
            if conn is not None:
                rows = conn.execute("SHOW TABLES").fetchall()
            else:
                # Open a lightweight read-only connection to check
                user_temp_dir = get_duckdb_cache_dir(user_id)
                ro_conn = duckdb.connect(
                    str(db_path),
                    read_only=True,
                    config={
                        'memory_limit': '500MB',
                        'temp_directory': str(user_temp_dir),
                        'access_mode': 'READ_ONLY',
                    }
                )
                try:
                    rows = ro_conn.execute("SHOW TABLES").fetchall()
                finally:
                    ro_conn.close()
            existing = {r[0] for r in rows}
            if table_name not in existing:
                logprint(f"🧹 [Database] Table '{table_name}' missing from DuckDB file; will recreate")
                return True
        except Exception as e:
            # If we cannot verify, assume existing and proceed; other checks still guard correctness
            logprint(f"⚠️ [Database] Could not verify table existence: {e}", level="warning")

        logprint(f"✅ [Database] Up-to-date; reusing table '{table_name}' in {db_path}")
        return False

    def _create_database(self, user_id: str, db_path: Path, file_path: str):
        """Create or update DuckDB database with table for source file"""
        table_name = self._get_table_name(file_path)
        logprint(
            f"🏗️ [Database] Creating/updating table '{table_name}' in database: {db_path}"
        )
        logprint(f"   Source file: {file_path}")
        logprint(f"   File type: {self._get_file_type(file_path)}")
        logprint(f"   File size: {os.path.getsize(file_path)} bytes")

        # Create database if it doesn't exist
        db_exists = db_path.exists()
        # Enforce memory cap and enable disk spilling for safety during creation
        user_temp_dir = get_duckdb_cache_dir(user_id)
        conn = duckdb.connect(
            str(db_path),
            config={"memory_limit": "500MB", "temp_directory": str(user_temp_dir)},
        )

        try:
            # Generate table name from filename
            table_name = self._get_table_name(file_path)

            # We will create or replace the table to ensure freshness

            # Determine file type and create table
            file_type = self._get_file_type(file_path)

            if file_type == "csv":
                sql = get_sql(
                    "create_or_replace_from_csv",
                    table_name=table_name,
                    file_path=file_path,
                )
                conn.execute(sql)
            elif file_type == "parquet":
                sql = get_sql(
                    "create_or_replace_from_parquet",
                    table_name=table_name,
                    file_path=file_path,
                )
                conn.execute(sql)
            elif file_type == "json":
                sql = get_sql(
                    "create_or_replace_from_json",
                    table_name=table_name,
                    file_path=file_path,
                )
                conn.execute(sql)
            elif file_type == "xlsx":
                # Prefer DuckDB excel extension for .xlsx; fallback to pandas if not available
                try:
                    conn.execute("LOAD excel")
                except duckdb.Error:
                    try:
                        conn.execute("INSTALL excel")
                        conn.execute("LOAD excel")
                    except duckdb.Error:
                        df = pd.read_excel(file_path)
                        conn.register("temp_df", df)
                        conn.execute(
                            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_df"
                        )
                    else:
                        sql = get_sql(
                            "create_or_replace_from_xlsx",
                            table_name=table_name,
                            file_path=file_path,
                        )
                        conn.execute(sql)
                else:
                    sql = get_sql(
                        "create_or_replace_from_xlsx",
                        table_name=table_name,
                        file_path=file_path,
                    )
                    conn.execute(sql)
            elif file_type == "xls":
                # Explicitly unsupported: do not attempt to ingest .xls
                raise RuntimeError(".xls files are not supported. Please convert to .xlsx or csv.")
            else:
                # Default to CSV
                sql = get_sql(
                    "create_or_replace_from_csv",
                    table_name=table_name,
                    file_path=file_path,
                )
                conn.execute(sql)

            # Compute stats and update catalog (SQLite)
            row_count = (
                conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone() or [0]
            )[0]

            logprint(
                f"✅ [Database] Successfully created table '{table_name}' with {row_count} rows"
            )
            logprint(f"   Database saved to: {db_path}")

            # Upsert datasets catalog record
            try:
                st = os.stat(file_path)
                upsert_dataset(
                    user_id=user_id,
                    file_path=file_path,
                    table_name=table_name,
                    file_size=st.st_size,
                    source_mtime=getattr(st, "st_mtime", st.st_ctime),
                    row_count=row_count,
                    file_type=file_type,
                )
            except Exception as e:
                logprint(
                    f"⚠️ [Database] Failed to upsert dataset catalog: {e}",
                    level="warning",
                )

        finally:
            conn.close()

    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from extension"""
        path = Path(file_path)
        suf = path.suffix.lower()
        if suf == ".csv":
            return "csv"
        elif suf == ".parquet":
            return "parquet"
        elif suf == ".json":
            return "json"
        elif suf == ".xlsx":
            return "xlsx"
        elif suf == ".xls":
            return "xls"
        else:
            return "csv"  # Default

    def _load_metadata(self, db_path: Path) -> Optional[dict]:
        """Load metadata for database (migrates legacy filename if needed)"""
        user_id = db_path.parent.name
        metadata_path = db_path.parent / f"{user_id}_dbmeta.json"
        legacy_path = db_path.parent / f"{user_id}_schema.json"

        # Check cache first
        if str(db_path) in self.metadata_cache:
            return self.metadata_cache[str(db_path)]

        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    self.metadata_cache[str(db_path)] = metadata
                    return metadata
            except:
                return None

        # Migrate legacy metadata file if present and looks like DB metadata
        if legacy_path.exists():
            try:
                with open(legacy_path, "r") as f:
                    legacy = json.load(f)
                if isinstance(legacy, dict) and "tables" in legacy:
                    self._save_metadata(db_path, legacy)
                    self.metadata_cache[str(db_path)] = legacy
                    return legacy
            except Exception:
                return None

        return None

    def _save_metadata(self, db_path: Path, metadata: dict):
        """Save metadata for database"""
        user_id = db_path.parent.name
        metadata_path = db_path.parent / f"{user_id}_dbmeta.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _update_last_accessed(self, db_path: Path):
        """Update last accessed time for database"""
        metadata = self._load_metadata(db_path)
        if metadata:
            metadata["last_accessed"] = datetime.now().isoformat()
            self._save_metadata(db_path, metadata)

    def close_connection(self, user_id: str, file_path: str):
        """Close connection for specific database"""
        db_path = self._get_database_path(user_id, file_path)
        db_path_str = str(db_path)

        if db_path_str in self.connections:
            self.connections[db_path_str].close()
            del self.connections[db_path_str]

    def cleanup_old_databases(self, max_age_days: int = 30):
        """Remove databases that haven't been accessed recently"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        for db_file in self.base_dir.rglob("*_data.duckdb"):
            metadata = self._load_metadata(db_file)
            if metadata:
                last_accessed = metadata.get("last_accessed")
                if last_accessed:
                    try:
                        last_accessed_dt = datetime.fromisoformat(last_accessed)
                        if last_accessed_dt < cutoff_time:
                            # Remove database and metadata
                            db_file.unlink()
                            user_id = db_file.parent.name
                            metadata_file = db_file.parent / f"{user_id}_schema.json"
                            if metadata_file.exists():
                                metadata_file.unlink()

                            # Remove from cache
                            db_path_str = str(db_file)
                            if db_path_str in self.connections:
                                self.connections[db_path_str].close()
                                del self.connections[db_path_str]
                    except:
                        continue

    def get_database_info(self, user_id: str, file_path: str) -> Optional[dict]:
        """Get information about a dataset from SQLite catalog"""
        db_path = self._get_database_path(user_id, file_path)
        try:
            from .database import get_dataset_by_path
            dataset = get_dataset_by_path(user_id, file_path)
            if not dataset:
                return None
            return {
                "database_path": str(db_path),
                "source_file": dataset.get("file_path"),
                "created_at": dataset.get("created_at"),
                "last_accessed": dataset.get("updated_at"),
                "file_size": dataset.get("file_size"),
                "row_count": dataset.get("row_count"),
                "file_type": dataset.get("file_type"),
            }
        except Exception:
            return None

    def shutdown(self):
        """Clean shutdown - close all connections"""
        for conn in self.connections.values():
            try:
                conn.close()
            except:
                pass
        self.connections.clear()
        self.metadata_cache.clear()
