"""
Utility helpers for managing user DuckDB databases and the datasets catalog.

Functions:
- list_duckdb_tables(user_id): List tables in the user's DuckDB database.
- delete_duckdb_table(user_id, table_name): Drop a table from the user's DuckDB database.
- list_sqlite_dataset_tables(user_id): List dataset table names recorded in SQLite for the user.

Safe to import and use from a shell/REPL. Does not modify app runtime state.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import re
import duckdb
import sqlite3


def _user_base_dir(user_id: str) -> Path:
    return Path.home() / ".inquira" / user_id


def _duckdb_path(user_id: str) -> Path:
    return _user_base_dir(user_id) / f"{user_id}_data.duckdb"


_IDENT_SAFE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _sql_ident(name: str) -> str:
    """Safely format an SQL identifier (table/column name)."""
    if _IDENT_SAFE_RE.match(name):
        return name
    # Escape double-quotes inside the identifier and wrap in quotes
    return '"' + name.replace('"', '""') + '"'


def list_duckdb_tables(user_id: str) -> List[str]:
    """Return a list of table names in the user's DuckDB database.

    Raises FileNotFoundError if the database file does not exist.
    """
    db_path = _duckdb_path(user_id)
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB file not found: {db_path}")

    # Ensure temp dir exists for spill
    tmp_dir = _user_base_dir(user_id) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Open in read-only mode to avoid conflicting with a write lock
    try:
        con = duckdb.connect(
            str(db_path),
            read_only=True,
            config={
                "memory_limit": "500MB",
                "temp_directory": str(tmp_dir),
                "access_mode": "READ_ONLY",
            },
        )
        try:
            rows = con.execute("SHOW TABLES").fetchall()
            return [r[0] for r in rows]
        finally:
            con.close()
    except duckdb.IOException:
        # Fall back to names recorded in the SQLite catalog
        return list_sqlite_dataset_tables(user_id)


def delete_duckdb_table(user_id: str, table_name: str) -> bool:
    """Drop a table from the user's DuckDB database.

    Returns True if executed successfully (even if the table didn't exist),
    raises FileNotFoundError if the DB does not exist.
    """
    db_path = _duckdb_path(user_id)
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB file not found: {db_path}")

    # Ensure temp dir exists for spill
    tmp_dir = _user_base_dir(user_id) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ident = _sql_ident(table_name)
    try:
        con = duckdb.connect(
            str(db_path),
            read_only=False,
            config={
                "memory_limit": "500MB",
                "temp_directory": str(tmp_dir),
            },
        )
        try:
            con.execute(f"DROP TABLE IF EXISTS {ident}")
            return True
        finally:
            con.close()
    except duckdb.IOException as e:
        raise RuntimeError(
            "DuckDB is locked by another process. Close app connections via "
            "POST /settings/close-connections or stop the server, then retry."
        ) from e


def list_sqlite_dataset_tables(user_id: str) -> List[str]:
    """Return a list of table names recorded in SQLite datasets for the user."""
    db_path = Path.home() / ".inquira" / "inquira.db"
    if not db_path.exists():
        return []

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT table_name FROM datasets WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        return [r[0] for r in rows if r and r[0]]
    finally:
        con.close()


__all__ = [
    "list_duckdb_tables",
    "delete_duckdb_table",
    "list_sqlite_dataset_tables",
    "username_to_user_id",
]


def username_to_user_id(username: str) -> Optional[str]:
    """Resolve a username to its user_id using the SQLite users table.

    Returns None if the user is not found.
    """
    try:
        # Prefer using the project's database helper if available
        from ..database import get_user_by_username  # type: ignore

        user = get_user_by_username(username)
        return user["user_id"] if user else None
    except Exception:
        # Fallback: direct SQLite query
        db_path = Path.home() / ".inquira" / "inquira.db"
        if not db_path.exists():
            return None
        con = sqlite3.connect(str(db_path))
        try:
            cur = con.cursor()
            cur.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            con.close()


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m inquira.utils.db_tools <list|catalog|delete> <user|username> [table]")
        sys.exit(1)

    cmd = args[0]
    ident = args[1] if len(args) > 1 else None
    if not ident:
        print("Missing user or username")
        sys.exit(1)

    # Heuristic: treat as user_id if it looks like a UUID, else resolve username
    uid = ident if (len(ident) >= 8 and '-' in ident) else username_to_user_id(ident)
    if not uid:
        print(f"Could not resolve user '{ident}' to user_id")
        sys.exit(2)

    if cmd == "list":
        try:
            tables = list_duckdb_tables(uid)
            print("DuckDB tables:", tables)
        except Exception as e:
            print(f"Error listing DuckDB tables: {e}")
            sys.exit(3)
    elif cmd == "catalog":
        print("Catalog tables:", list_sqlite_dataset_tables(uid))
    elif cmd == "delete":
        if len(args) < 3:
            print("Usage: python -m inquira.utils.db_tools delete <user|username> <table>")
            sys.exit(1)
        table = args[2]
        try:
            ok = delete_duckdb_table(uid, table)
            print("Deleted" if ok else "No-op")
        except Exception as e:
            print(f"Error deleting table: {e}")
            print("Hint: call POST /settings/close-connections or stop the server, then retry.")
            sys.exit(4)
    else:
        print("Unknown command. Use list | catalog | delete")
        sys.exit(1)
