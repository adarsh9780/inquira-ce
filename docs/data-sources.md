# Local data-source contract

All local adapters implement the same lifecycle:

1. Discover the source and its selectable objects.
2. Preview at most 1,000 rows without limiting ingestion.
3. Materialize selected objects into immutable Parquet snapshots.
4. Publish the snapshots atomically through the Go control plane.
5. Refresh only when the source fingerprint changes.

| Adapter | Extensions | Selectable objects | Snapshot behavior |
| --- | --- | --- | --- |
| CSV | `.csv` | File | One Parquet table |
| Parquet | `.parquet` | File | One canonical Parquet table |
| Excel | `.xlsx` | Sheets | One Parquet table per selected sheet |
| JSON | `.json`, `.jsonl`, `.ndjson` | File | One Parquet table; nested values are preserved |
| SQLite | `.sqlite`, `.sqlite3`, `.db` | User tables and views | One Parquet table per selected object |

## SQLite safety boundary

SQLite sources are opened with `mode=ro`, query-only mode, disabled extension
loading, and a bounded busy timeout. Discovery reads only schema metadata, so a
database with many or very large tables remains responsive. Previews are
bounded to at most 1,000 rows. Materialization uses a read transaction and
streams rows in bounded batches. The source database is never attached to the
workspace catalog, and analysis only reads the resulting snapshots.

The source database, write-ahead log, and rollback journal participate in the
fingerprint. If those files change during discovery or materialization, the
operation fails rather than publishing a potentially inconsistent snapshot.

## Deliberate limits

- Legacy Excel `.xls`, compressed CSV, XML, and DuckDB database connections are
  not accepted.
- JSON support targets arrays/objects and newline-delimited records. A malformed
  or schema-less source fails during discovery.
- SQLite internal `sqlite_*` objects and hidden virtual-table columns are not
  exposed.
- A refresh that removes a selected Excel sheet, SQLite table, or SQLite view
  enters `needs_attention` instead of silently changing the workspace schema.
