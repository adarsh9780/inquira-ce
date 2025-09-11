import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import duckdb
import pandas as pd
from .config_models import AppConfig


class DatabaseManager:
    """
    Manages persistent DuckDB databases for efficient data access.
    Converts CSV files to DuckDB databases on first access and reuses them.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        # Use user's home directory for persistent storage
        self.base_dir = Path.home() / '.inquira'
        self.databases_dir = self.base_dir / 'databases'
        self.databases_dir.mkdir(parents=True, exist_ok=True)

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
        needs_recreation = self._should_recreate_database(db_path, file_path)
        if needs_recreation:
            print(f"🔧 [Database] Creating/updating database for user {user_id}: {file_path}")
            self._create_database(db_path, file_path)
        else:
            print(f"♻️ [Database] Reusing existing database for user {user_id}: {file_path}")

        # Get or create connection
        if str(db_path) not in self.connections:
            print(f"🔌 [Database] Creating new connection to: {db_path}")
            self.connections[str(db_path)] = duckdb.connect(str(db_path))
        else:
            print(f"🔗 [Database] Reusing existing connection to: {db_path}")

        # Update last accessed time
        self._update_last_accessed(db_path)

        return self.connections[str(db_path)]

    def get_existing_connection(self, user_id: str) -> Optional[duckdb.DuckDBPyConnection]:
        """
        Get existing database connection for a user without creating new database.
        Returns None if database doesn't exist.
        """
        db_path = self.base_dir / user_id / f"{user_id}_data.duckdb"

        if not db_path.exists():
            return None

        # Get or create connection
        if str(db_path) not in self.connections:
            self.connections[str(db_path)] = duckdb.connect(str(db_path))

        # Update last accessed time
        self._update_last_accessed(db_path)

        return self.connections[str(db_path)]

    def _get_database_path(self, user_id: str, file_path: str) -> Path:
        """Generate consistent database file path"""
        # Create user-specific directory
        user_dir = self.base_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Each user has one database file for all their data
        return user_dir / f"{user_id}_data.duckdb"

    def _get_table_name(self, file_path: str) -> str:
        """Generate table name from file path"""
        # Use filename without extension, replace special chars with underscores
        filename = Path(file_path).stem
        # Replace any non-alphanumeric characters with underscores
        table_name = ''.join(c if c.isalnum() else '_' for c in filename)
        # Ensure it starts with a letter
        if table_name and not table_name[0].isalpha():
            table_name = f"t_{table_name}"
        # Ensure it's not empty
        if not table_name:
            table_name = "data_table"
        return table_name.lower()

    def _should_recreate_database(self, db_path: Path, file_path: str) -> bool:
        """Check if table needs to be created/updated"""
        table_name = self._get_table_name(file_path)

        # Database doesn't exist
        if not db_path.exists():
            print(f"📁 [Database] Database doesn't exist, creating: {db_path}")
            return True

        # Source file doesn't exist
        if not os.path.exists(file_path):
            print(f"❌ [Database] Source file doesn't exist: {file_path}")
            return True

        # Check metadata for table information
        metadata = self._load_metadata(db_path)
        if not metadata or 'tables' not in metadata:
            print(f"📋 [Database] No metadata found, recreating database")
            return True

        # Check if table exists in metadata
        if table_name not in metadata['tables']:
            print(f"📊 [Database] Table '{table_name}' not found in metadata, creating")
            return True

        table_info = metadata['tables'][table_name]

        # Check if source file was modified after table creation
        source_mtime = os.path.getmtime(file_path)
        table_creation_time = table_info.get('created_at', 0)

        # Convert ISO string to timestamp if needed
        if isinstance(table_creation_time, str):
            try:
                table_creation_time = datetime.fromisoformat(table_creation_time).timestamp()
            except:
                print(f"⚠️ [Database] Could not parse creation time, recreating")
                return True

        # Compare modification times
        if source_mtime > table_creation_time:
            print(f"🔄 [Database] File modified after database creation:")
            print(f"   File mtime: {datetime.fromtimestamp(source_mtime)}")
            print(f"   DB created: {datetime.fromtimestamp(table_creation_time)}")
            print(f"   Recreating database for: {file_path}")
            return True
        else:
            print(f"✅ [Database] File unchanged, reusing existing database:")
            print(f"   File: {file_path}")
            print(f"   Table: {table_name}")
            print(f"   Database: {db_path}")
            return False

    def _create_database(self, db_path: Path, file_path: str):
        """Create or update DuckDB database with table for source file"""
        table_name = self._get_table_name(file_path)
        print(f"🏗️ [Database] Creating/updating table '{table_name}' in database: {db_path}")
        print(f"   Source file: {file_path}")
        print(f"   File type: {self._get_file_type(file_path)}")
        print(f"   File size: {os.path.getsize(file_path)} bytes")

        # Create database if it doesn't exist
        db_exists = db_path.exists()
        conn = duckdb.connect(str(db_path))

        try:
            # Generate table name from filename
            table_name = self._get_table_name(file_path)

            # Check if table already exists
            existing_tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [row[0] for row in existing_tables]

            if table_name in table_names:
                print(f"Table '{table_name}' already exists in database")
                return

            # Determine file type and create table
            file_type = self._get_file_type(file_path)

            if file_type == 'csv':
                conn.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_csv_auto('{file_path}')
                """)
            elif file_type == 'parquet':
                conn.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_parquet('{file_path}')
                """)
            elif file_type == 'json':
                conn.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_json_auto('{file_path}')
                """)
            elif file_type in ['xlsx', 'xls']:
                # Handle Excel files with pandas
                df = pd.read_excel(file_path)
                conn.register('temp_df', df)
                conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            else:
                # Default to CSV
                conn.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_csv_auto('{file_path}')
                """)

            # Load or create metadata
            if db_exists:
                metadata = self._load_metadata(db_path) or {}
                if 'tables' not in metadata:
                    metadata['tables'] = {}
            else:
                metadata = {
                    'database_created': datetime.now().isoformat(),
                    'last_accessed': datetime.now().isoformat(),
                    'tables': {}
                }

            # Add table metadata
            table_info = {
                'source_file': file_path,
                'source_mtime': os.path.getmtime(file_path),
                'created_at': datetime.now().isoformat(),
                'file_size': os.path.getsize(file_path),
                'row_count': (conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone() or [0])[0],
                'file_type': file_type
            }
            metadata['tables'][table_name] = table_info
            metadata['last_accessed'] = datetime.now().isoformat()

            self._save_metadata(db_path, metadata)
            self.metadata_cache[str(db_path)] = metadata

            print(f"✅ [Database] Successfully created table '{table_name}' with {table_info['row_count']} rows")
            print(f"   Database saved to: {db_path}")

        finally:
            conn.close()

    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from extension"""
        path = Path(file_path)
        if path.suffix.lower() == '.csv':
            return 'csv'
        elif path.suffix.lower() == '.parquet':
            return 'parquet'
        elif path.suffix.lower() == '.json':
            return 'json'
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            return 'excel'
        else:
            return 'csv'  # Default

    def _load_metadata(self, db_path: Path) -> Optional[dict]:
        """Load metadata for database"""
        user_id = db_path.parent.name
        metadata_path = db_path.parent / f"{user_id}_schema.json"

        # Check cache first
        if str(db_path) in self.metadata_cache:
            return self.metadata_cache[str(db_path)]

        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.metadata_cache[str(db_path)] = metadata
                    return metadata
            except:
                return None

        return None

    def _save_metadata(self, db_path: Path, metadata: dict):
        """Save metadata for database"""
        user_id = db_path.parent.name
        metadata_path = db_path.parent / f"{user_id}_schema.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _update_last_accessed(self, db_path: Path):
        """Update last accessed time for database"""
        metadata = self._load_metadata(db_path)
        if metadata:
            metadata['last_accessed'] = datetime.now().isoformat()
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
                last_accessed = metadata.get('last_accessed')
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
        """Get information about a database"""
        db_path = self._get_database_path(user_id, file_path)
        metadata = self._load_metadata(db_path)

        if metadata:
            return {
                'database_path': str(db_path),
                'source_file': metadata.get('source_file'),
                'created_at': metadata.get('created_at'),
                'last_accessed': metadata.get('last_accessed'),
                'file_size': metadata.get('file_size'),
                'row_count': metadata.get('row_count'),
                'file_type': metadata.get('file_type')
            }

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