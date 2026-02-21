/**
 * DuckDB-WASM Service
 * 
 * Singleton that manages a browser-native DuckDB instance.
 * Uses registerFileHandle for lazy/streamed file reading — the user's
 * file is never fully loaded into a JS ArrayBuffer.
 * 
 * Exposes window._duckdb_query so Python code in Pyodide can call
 * SQL against this same DuckDB instance via the FFI bridge.
 */

import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_eh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

class DuckDBService {
    constructor() {
        this.db = null;
        this.conn = null;
        this._initPromise = null;
    }

    /**
     * Boot the DuckDB-WASM worker. Safe to call multiple times.
     */
    async initialize() {
        if (this.db && this.conn) return this.db;
        if (this._initPromise) return this._initPromise;

        this._initPromise = this._boot();
        return this._initPromise;
    }

    async _boot() {
        try {
            console.debug('[DuckDB-WASM] Initializing...');

            const MANUAL_BUNDLES = {
                mvp: {
                    mainModule: duckdb_wasm,
                    mainWorker: mvp_worker,
                },
                eh: {
                    mainModule: duckdb_wasm_eh,
                    mainWorker: eh_worker,
                },
            };

            const bundle = await duckdb.selectBundle(MANUAL_BUNDLES);
            const worker = new Worker(bundle.mainWorker);
            const logger = new duckdb.ConsoleLogger();
            this.db = new duckdb.AsyncDuckDB(logger, worker);
            await this.db.instantiate(bundle.mainModule, bundle.pthreadWorker);

            this.conn = await this.db.connect();
            console.debug('[DuckDB-WASM] Ready.');

            // Expose query function globally so Pyodide Python can call it
            window._duckdb_query = this.query.bind(this);
            window._duckdb_query_arrow = this.queryArrowBytes.bind(this);

            return this.db;
        } catch (err) {
            console.error('[DuckDB-WASM] Init failed:', err);
            this.db = null;
            this.conn = null;
            this._initPromise = null;
            throw err;
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // File Ingestion (lazy streaming via registerFileHandle)
    // ─────────────────────────────────────────────────────────────────

    /**
     * Ingest a user-selected File into DuckDB via lazy streaming.
     * 
     * @param {File} file - Browser File object from <input type="file">
     * @returns {{ tableName: string, columns: Array<{name: string, type: string}>, rowCount: number }}
     */
    async ingestFile(file) {
        await this.initialize();

        // Derive a safe SQL table name from the filename
        const tableName = file.name
            .replace(/\.[^.]+$/, '')              // strip extension
            .replace(/[^a-zA-Z0-9_]/g, '_')       // replace special chars
            .replace(/^(\d)/, '_$1')               // can't start with digit
            .toLowerCase();

        console.debug(`[DuckDB-WASM] Ingesting "${file.name}" as table "${tableName}"...`);

        // Register the File handle — DuckDB will read pages on demand
        // via File.slice(), NOT loading the entire file into memory.
        await this.db.registerFileHandle(file.name, file, duckdb.DuckDBDataProtocol.BROWSER_FILEREADER, true);

        // Ask DuckDB to create a persistent table from the file
        // DuckDB auto-detects CSV, Parquet, JSON by extension
        await this.conn.query(`
            CREATE OR REPLACE TABLE ${tableName} AS 
            SELECT * FROM '${file.name}'
        `);

        // Get column metadata
        const descResult = await this.conn.query(`DESCRIBE ${tableName}`);
        const columns = descResult.toArray().map(row => ({
            name: row.column_name,
            type: row.column_type,
        }));

        // Get row count
        const countResult = await this.conn.query(`SELECT count(*) as cnt FROM ${tableName}`);
        const rowCount = Number(countResult.toArray()[0].cnt);

        console.debug(`[DuckDB-WASM] Table "${tableName}" created: ${rowCount} rows, ${columns.length} columns.`);

        return { tableName, columns, rowCount };
    }

    // ─────────────────────────────────────────────────────────────────
    // Query Execution
    // ─────────────────────────────────────────────────────────────────

    /**
     * Execute SQL and return results as an array of plain JS objects.
     * Used by the Python FFI bridge (window._duckdb_query).
     * 
     * @param {string} sql
     * @returns {Array<Object>}
     */
    async query(sql) {
        await this.initialize();
        const result = await this.conn.query(sql);
        return result.toArray().map(row => ({ ...row }));
    }

    /**
     * Execute SQL and return results as serialized Arrow IPC bytes.
     * Used by the Pyodide bridge to pass Arrow data to Python efficiently.
     * 
     * @param {string} sql
     * @returns {Uint8Array} Arrow IPC stream bytes
     */
    async queryArrowBytes(sql) {
        await this.initialize();
        const result = await this.conn.query(sql);
        // The result IS an Arrow Table — serialize to IPC
        const writer = await import('apache-arrow').catch(() => null);
        if (writer) {
            const { tableToIPC } = writer;
            return tableToIPC(result);
        }
        // Fallback: return as plain JSON-serializable objects
        return result.toArray().map(row => ({ ...row }));
    }

    // ─────────────────────────────────────────────────────────────────
    // Metadata
    // ─────────────────────────────────────────────────────────────────

    /**
     * List all table names in the database.
     */
    async getTableNames() {
        await this.initialize();
        if (!this.conn) return [];
        const result = await this.conn.query(`SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'`);
        return result.toArray().map(row => row.table_name);
    }

    /**
     * Get column info for a table.
     */
    async describeTable(tableName) {
        await this.initialize();
        const result = await this.conn.query(`DESCRIBE ${tableName}`);
        return result.toArray().map(row => ({
            name: row.column_name,
            type: row.column_type,
        }));
    }

    /**
     * Drop a table.
     */
    async dropTable(tableName) {
        await this.initialize();
        await this.conn.query(`DROP TABLE IF EXISTS ${tableName}`);
    }
}

// Export a singleton
export const duckdbService = new DuckDBService();
