#!/usr/bin/env python3
"""
Inspect DuckDB database tables.

Usage:
    python scripts/debug/inspect_duckdb.py <username>

Example:
    python scripts/debug/inspect_duckdb.py adarshmaurya

NOTE: DuckDB supports multiple READ-ONLY connections in parallel.
      This script uses read_only=True, so it's SAFE to run while the backend is running.
"""

import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb not installed. Run: pip install duckdb")
    sys.exit(1)


def inspect_duckdb(username: str):
    """Inspect DuckDB database for a given username."""
    
    # Build the path: ~/.inquira/{username}/{username}_data.duckdb
    db_path = Path.home() / ".inquira" / username / f"{username}_data.duckdb"
    
    print(f"📂 Database path: {db_path}")
    
    if not db_path.exists():
        print(f"❌ Database file does not exist!")
        return
    
    print(f"✅ Database file exists ({db_path.stat().st_size / 1024:.1f} KB)")
    print()
    
    # Connect in READ-ONLY mode (safe for parallel access with other readers)
    # NOTE: DuckDB doesn't allow any new connections when a write lock is held
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
    except Exception as e:
        error_str = str(e)
        if "lock" in error_str.lower() or "conflicting" in error_str.lower():
            print(f"❌ Cannot connect: Database is locked by another process")
            print()
            print("💡 Solutions:")
            print("   1. Stop the backend server temporarily:")
            print("      - Press Ctrl+C in the terminal running 'uv run inquira'")
            print("      - Run this script")
            print("      - Restart the backend with 'uv run inquira'")
            print()
            print("   2. Or use the API endpoint to check tables:")
            print("      curl http://localhost:8000/datasets/list")
        else:
            print(f"❌ Failed to connect: {e}")
        return
    
    # List all tables
    print("📋 Tables in database:")
    print("-" * 60)
    
    try:
        tables = conn.execute("SHOW TABLES").fetchall()
        
        if not tables:
            print("   (No tables found)")
        else:
            for i, (table_name,) in enumerate(tables, 1):
                # Get row count for each table
                try:
                    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    
                    # Get column info
                    columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
                    col_names = [col[0] for col in columns]
                    
                    print(f"   {i}. {table_name}")
                    print(f"      Rows: {row_count:,}")
                    print(f"      Columns ({len(col_names)}): {', '.join(col_names[:5])}{'...' if len(col_names) > 5 else ''}")
                    print()
                except Exception as e:
                    print(f"   {i}. {table_name} (error reading: {e})")
        
        print("-" * 60)
        print(f"Total tables: {len(tables)}")
        
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable usernames:")
        inquira_dir = Path.home() / ".inquira"
        if inquira_dir.exists():
            for item in inquira_dir.iterdir():
                if item.is_dir():
                    db_file = item / f"{item.name}_data.duckdb"
                    if db_file.exists():
                        print(f"   - {item.name}")
        sys.exit(1)
    
    username = sys.argv[1]
    inspect_duckdb(username)


if __name__ == "__main__":
    main()
