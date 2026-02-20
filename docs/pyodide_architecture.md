# Pyodide and WebAssembly Architecture

## The 4GB WebAssembly Memory Limit
WebAssembly (Wasm32) environments like Pyodide have a hard memory limit of 4GB. Traditional in-memory data science tools like Pandas require significantly more memory than the size of the dataset (e.g., a 2GB CSV file can require 6GB+ of RAM to process). Attempting to load large datasets directly into Pandas within Pyodide will cause an Out of Memory (OOM) crash in the browser tab.

## How We Bypass the Limit

We bypass this limitation by using an architecture comprised of **DuckDB-Wasm**, **HTTP Range Requests**, and **Ibis**.

### 1. Out-of-Core Execution (DuckDB)
DuckDB is an "out-of-core" analytical database. Instead of loading an entire dataset into memory, DuckDB streams data from storage in small, optimized "vectorized chunks", processes them, and discards them. It only keeps the final results of a query in memory. This allows it to process datasets significantly larger than the available RAM or the 4GB WebAssembly limit.

### 2. HTTP Range Requests (Network Optimizations)
DuckDB-Wasm does not download the entire dataset to the browser. Instead, it uses modern HTTP Range Requests to fetch only the specific byte ranges required to answer a query. For instance, if you query `SELECT column_A FROM massive_table LIMIT 10` from a Parquet file, DuckDB reads the file metadata and fetches only the relevant bytes over the network, completely avoiding the transfer and memory overhead of the whole file.

### 3. Lazy Evaluation (Ibis)
We use Ibis as the bridge between the AI agent and DuckDB. Ibis uses "lazy evaluation"—it builds an execution plan as the agent writes data manipulation code (e.g., `table.group_by('state').count()`). Nothing happens in memory until `.execute()` is called. 
When executed, Ibis compiles the plan to an optimized SQL string, sends it to DuckDB, which streams the targeted data chunks, and returns a small result table back to Pyodide/Pandas.

### Remaining Limitations
The 4GB limit is only a constraint when:
- Attempting to display or materialize massively large *final* result sets (e.g., a query returning 3GB of raw rows that must all be held in memory).
- Utilizing heavy in-memory algorithms, such as training an `sklearn` machine learning model on large datasets, as standard ML libraries cannot leverage out-of-core network streaming in this environment.
