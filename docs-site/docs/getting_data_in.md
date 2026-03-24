# Getting Data In

Inquira CE provides a zero-friction, incredibly fast mechanism for analyzing local files without requiring any cloud uploads or fragile in-memory loaders.

## Supported Formats
You can connect and ingest the following local file extensions:
- **Comma-Separated Values:** `.csv`
- **Tab-Separated Values:** `.tsv`
- **Excel Spreadsheets:** `.xlsx`, `.xls`
- **JSON Data:** `.json`
- **Apache Parquet:** `.parquet`

## How Ingestion Works
Rather than fighting with Pandas `read_csv()` memory limits inside the agent, Inquira strictly shifts data management to the analytical engine: **DuckDB**.

### 1. Zero Cloud Uploads
When you drag and drop a file (or use the system file picker via Tauri), that file never leaves your computer. The system simply fetches the absolute path of the local file.

### 2. High-Speed Relational Conversion
Once the file path is recognized, the backend transparently instructs the local **Workspace Kernel** to execute a lightning-fast DuckDB ingestion command:
```sql
CREATE TABLE <your_data> AS FROM '<local_absolute_path>'
```
This bypasses memory bottlenecks. Even for multiple-gigabyte Parquet or CSV files, DuckDB streams and translates them instantly into strongly-typed relational tables within your project.

### 3. Schema Metadata Generation
Once the data is ingested into DuckDB, Inquira automatically evaluates the generated table to build a schema artifact (`metadata.json`). This JSON map informs the Agent Planner about column names, data types, and brief descriptions—allowing the AI to write perfectly accurate SQL and Python code against your data without actually needing to "see" every row.

## Smart File Synchronization
Inquira CE values idempotency and speed. When you reload a workspace, Inquira compares the **file size** and **modified time (mtime)** of your source files against the cached DuckDB tables. 
- If the file is exactly the same, Inquira instantly loads from the local cached DuckDB binary. 
- If the source file was updated externally (like appending new rows to an Excel sheet), Inquira transparently drops the old table and re-ingests the fresh data—guaranteeing your agent always sees the absolute latest truth.
