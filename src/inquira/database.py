import sqlite3
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
import json
from .fingerprint import file_fingerprint_md5
from .logger import logprint

# Database file path
DB_PATH = Path.home() / ".inquira" / "inquira.db"

def get_db_connection():
    """Get a database connection"""
    return sqlite3.connect(str(DB_PATH))

def init_database():
    """Initialize the database and create tables if they don't exist"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create settings table with foreign key to users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            user_id TEXT PRIMARY KEY,
            api_key TEXT,
            data_path TEXT,
            schema_path TEXT,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')

    # Create sessions table for session management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            data_file_path TEXT,
            schema_file_path TEXT,
            api_key TEXT,
            selected_model TEXT,
            python_file_content TEXT,
            chat_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')

    # Create datasets catalog table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            table_name TEXT NOT NULL,
            schema_path TEXT,
            file_size INTEGER,
            source_mtime REAL,
            -- New columns may be added via migration below
            row_count INTEGER,
            file_type TEXT,
            last_accessed TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, file_hash),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')

    # Lightweight migrations: ensure optional columns exist
    try:
        cursor.execute("PRAGMA table_info(datasets)")
        cols = {row[1] for row in cursor.fetchall()}
        if 'row_count' not in cols:
            cursor.execute("ALTER TABLE datasets ADD COLUMN row_count INTEGER")
        if 'file_type' not in cols:
            cursor.execute("ALTER TABLE datasets ADD COLUMN file_type TEXT")
        if 'last_accessed' not in cols:
            cursor.execute("ALTER TABLE datasets ADD COLUMN last_accessed TIMESTAMP")
    except Exception:
        pass

    conn.commit()
    conn.close()

def migrate_json_to_sqlite():
    """Migrate existing JSON data to SQLite database"""
    users_file = Path.home() / ".inquira" / "users.json"

    if not users_file.exists():
        logprint("No existing JSON data to migrate")
        return

    try:
        with open(users_file, 'r') as f:
            users_data = json.load(f)

        conn = get_db_connection()
        cursor = conn.cursor()

        for user_id, user_data in users_data.items():
            # Insert user - handle both old and new format
            salt = user_data.get('salt', secrets.token_hex(16))  # Generate salt if not exists
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, password_hash, salt)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                user_data.get('username', f'user_{user_id}'),
                user_data.get('password_hash', ''),
                salt
            ))

            # Insert settings if they exist
            settings = user_data.get('settings', {})
            if settings:
                cursor.execute('''
                    INSERT OR REPLACE INTO settings
                    (user_id, api_key, data_path, schema_path, context)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    settings.get('api_key'),
                    settings.get('data_path'),
                    settings.get('schema_path'),
                    settings.get('context')
                ))

        conn.commit()
        conn.close()

        # Backup the old JSON file
        backup_file = users_file.with_suffix('.json.backup')
        users_file.rename(backup_file)
        logprint(f"✅ Migration completed. Original file backed up as {backup_file}")

    except Exception as e:
        logprint(f"❌ Migration failed: {e}", level="error")

# Initialize database on module import
init_database()

# User operations
def create_user(user_id: str, username: str, password_hash: str, salt: str) -> bool:
    """Create a new user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO users (user_id, username, password_hash, salt)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, password_hash, salt))

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# Datasets catalog operations
def upsert_dataset(
    user_id: str,
    file_path: str,
    table_name: str,
    file_size: int,
    source_mtime: float,
    row_count: int | None = None,
    file_type: str | None = None,
) -> bool:
    """Insert or update a dataset record based on user+file_hash, including stats."""
    try:
        file_hash = file_fingerprint_md5(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO datasets (user_id, file_path, file_hash, table_name, file_size, source_mtime, row_count, file_type, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, file_hash) DO UPDATE SET
                file_path = excluded.file_path,
                table_name = excluded.table_name,
                file_size = excluded.file_size,
                source_mtime = excluded.source_mtime,
                row_count = COALESCE(excluded.row_count, datasets.row_count),
                file_type = COALESCE(excluded.file_type, datasets.file_type),
                last_accessed = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        ''', (user_id, file_path, file_hash, table_name, file_size, source_mtime, row_count, file_type))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error upserting dataset: {e}", level="error")
        return False

def set_dataset_schema_path(user_id: str, file_path: str, schema_path: str) -> bool:
    """Set schema_path for a dataset by user and file path (computed hash)"""
    try:
        file_hash = file_fingerprint_md5(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE datasets SET schema_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND file_hash = ?
        ''', (schema_path, user_id, file_hash))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error updating dataset schema_path: {e}", level="error")
        return False

def touch_dataset_last_accessed(user_id: str, file_path: str) -> bool:
    """Update last_accessed for a dataset to CURRENT_TIMESTAMP"""
    try:
        file_hash = file_fingerprint_md5(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE datasets SET last_accessed = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND file_hash = ?
        ''', (user_id, file_hash))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error touching dataset last_accessed: {e}", level="error")
        return False

def get_dataset_by_path(user_id: str, file_path: str) -> Optional[Dict[str, Any]]:
    try:
        file_hash = file_fingerprint_md5(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, file_path, file_hash, table_name, schema_path,
                   file_size, source_mtime, row_count, file_type, last_accessed,
                   created_at, updated_at
            FROM datasets WHERE user_id = ? AND file_hash = ?
        ''', (user_id, file_hash))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0], 'user_id': row[1], 'file_path': row[2], 'file_hash': row[3],
                'table_name': row[4], 'schema_path': row[5], 'file_size': row[6],
                'source_mtime': row[7], 'row_count': row[8], 'file_type': row[9],
                'last_accessed': row[10], 'created_at': row[11], 'updated_at': row[12]
            }
        return None
    except Exception as e:
        logprint(f"Error getting dataset: {e}", level="error")
        return None

def list_datasets(user_id: str) -> list[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, file_path, file_hash, table_name, schema_path,
                   file_size, source_mtime, row_count, file_type, last_accessed,
                   created_at, updated_at
            FROM datasets WHERE user_id = ? ORDER BY updated_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                'id': row[0], 'user_id': row[1], 'file_path': row[2], 'file_hash': row[3],
                'table_name': row[4], 'schema_path': row[5], 'file_size': row[6],
                'source_mtime': row[7], 'row_count': row[8], 'file_type': row[9],
                'last_accessed': row[10], 'created_at': row[11], 'updated_at': row[12]
            })
        return result
    except Exception as e:
        logprint(f"Error listing datasets: {e}", level="error")
        return []
    except Exception:
        return False

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'password_hash': row[2],
            'salt': row[3],  # Salt is actually in column 3
            'created_at': row[4],  # Created_at is in column 4
            'updated_at': row[5]   # Updated_at is in column 5
        }
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by user_id"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'password_hash': row[2],
            'salt': row[3],  # Salt is actually in column 3
            'created_at': row[4],  # Created_at is in column 4
            'updated_at': row[5]   # Updated_at is in column 5
        }
    return None

def update_user_password(user_id: str, new_password_hash: str, new_salt: str) -> bool:
    """Update user's password hash and salt"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users
            SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_password_hash, new_salt, user_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error updating password: {e}", level="error")
        return False

# Settings operations
def get_user_settings(user_id: str) -> Dict[str, Any]:
    """Get user settings"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM settings WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'user_id': row[0],
            'api_key': row[1],
            'data_path': row[2],
            'schema_path': row[3],
            'context': row[4],
            'created_at': row[5],
            'updated_at': row[6]
        }
    return {}

def save_user_settings(user_id: str, settings: Dict[str, Any]) -> bool:
    """Save or update user settings"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO settings
            (user_id, api_key, data_path, schema_path, context)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            settings.get('api_key'),
            settings.get('data_path'),
            settings.get('schema_path'),
            settings.get('context')
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error saving settings: {e}", level="error")
        return False

# Session operations
def create_session(session_id: str, user_id: str, session_data: Dict[str, Any]) -> bool:
    """Create a new session"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO sessions
            (session_id, user_id, data_file_path, schema_file_path, api_key,
             selected_model, python_file_content, chat_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            user_id,
            session_data.get('data_file_path'),
            session_data.get('schema_file_path'),
            session_data.get('api_key'),
            session_data.get('selected_model'),
            session_data.get('python_file_content'),
            json.dumps(session_data.get('chat_history', []))
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error creating session: {e}", level="error")
        return False

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session by session_id"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'session_id': row[0],
            'user_id': row[1],
            'data_file_path': row[2],
            'schema_file_path': row[3],
            'api_key': row[4],
            'selected_model': row[5],
            'python_file_content': row[6],
            'chat_history': json.loads(row[7]) if row[7] else [],
            'created_at': row[8],
            'updated_at': row[9]
        }
    return None

def update_session(session_id: str, session_data: Dict[str, Any]) -> bool:
    """Update session data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build dynamic update query
        update_fields = []
        values = []

        for field in ['data_file_path', 'schema_file_path', 'api_key',
                     'selected_model', 'python_file_content']:
            if field in session_data:
                update_fields.append(f"{field} = ?")
                values.append(session_data[field])

        if update_fields:
            query = f"UPDATE sessions SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?"
            values.append(session_id)

            cursor.execute(query, values)
            conn.commit()

        conn.close()
        return True
    except Exception as e:
        logprint(f"Error updating session: {e}", level="error")
        return False

def add_chat_message(session_id: str, message: Dict[str, Any]) -> bool:
    """Add a chat message to session"""
    try:
        session = get_session(session_id)
        if not session:
            return False

        chat_history = session['chat_history']
        chat_history.append({
            'id': len(chat_history),
            'question': message.get('question', ''),
            'explanation': message.get('explanation', ''),
            'timestamp': message.get('timestamp', '')
        })

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE sessions
            SET chat_history = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (json.dumps(chat_history), session_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error adding chat message: {e}", level="error")
        return False

def delete_user_settings(user_id: str) -> bool:
    """Delete all settings for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM settings WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logprint(f"Error deleting settings: {e}", level="error")
        return False

def delete_user_account(user_id: str) -> bool:
    """Delete a user account and all associated data (CASCADE delete)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete the user - this will CASCADE delete settings and sessions due to foreign key constraints
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

        # Check if deletion was successful
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    except Exception as e:
        logprint(f"Error deleting user account: {e}", level="error")
        return False
