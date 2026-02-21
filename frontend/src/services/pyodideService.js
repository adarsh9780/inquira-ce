import { loadPyodide } from 'pyodide';
import apiService from './apiService.js';
import { duckdbService } from './duckdbService.js';
import { ensureExecutionTableReady } from '../utils/executionTableGuard.js';

class PyodideService {
    constructor() {
        this.pyodide = null;
        this.initializationPromise = null;
        this.accumulatedCode = ''; // Track all previously run code
        this.isInitializing = false;
    }

    /**
     * Initialize Pyodide, install micropip, ibis, and duckdb
     */
    async initialize(options = {}) {
        if (this.pyodide) return this.pyodide;

        if (this.initializationPromise) {
            return this.initializationPromise;
        }

        this.isInitializing = true;
        this._onProgress = options.onProgress || (() => { });
        this.initializationPromise = this._initPyodide();
        return this.initializationPromise;
    }

    async _initPyodide() {
        try {
            console.debug('Attempting to load Pyodide...');

            // Fetch backend URL from config for the fallback
            let backendUrl = 'http://localhost:8000';
            if (typeof window !== 'undefined') {
                if (import.meta.env.VITE_API_BASE) {
                    backendUrl = import.meta.env.VITE_API_BASE;
                } else if (!import.meta.env.DEV) {
                    backendUrl = window.location.origin;
                }
            }
            backendUrl = backendUrl.replace(/\/+$/, '');
            const localIndexURL = `${backendUrl}/assets/pyodide/`;
            const cdnIndexURL = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/';

            // 1. Try public CDN first. If blocked by corporate proxy, fallback to self-hosted Wasm.
            try {
                this.pyodide = await loadPyodide({ indexURL: cdnIndexURL });
                console.debug('Pyodide successfully loaded from public CDN.');
            } catch (cdnError) {
                console.warn('Pyodide CDN blocked or unreachable, falling back to backend self-hosted Wasm...', cdnError);
                try {
                    this.pyodide = await loadPyodide({ indexURL: localIndexURL });
                    console.debug('Pyodide successfully loaded from backend fallback.');
                } catch (localError) {
                    console.error('Both CDN and backend Pyodide endpoints failed to load.');
                    throw localError;
                }
            }

            console.debug('Pyodide loaded. Installing micropip...');
            await this.pyodide.loadPackage('micropip');
            const micropip = this.pyodide.pyimport('micropip');

            // 2. Configure PyPI or JFrog Mirror
            let installKwargs = {};
            if (typeof window !== 'undefined' && import.meta.env.VITE_PYPI_MIRROR_URL) {
                console.debug(`Using custom Python package index: ${import.meta.env.VITE_PYPI_MIRROR_URL}`);
                installKwargs = { index_url: import.meta.env.VITE_PYPI_MIRROR_URL };
            }

            console.debug('Installing Ibis, Pandas, PyArrow, and Plotly...');
            this._onProgress('packages');
            // No [duckdb] extra — Python duckdb is NOT used.
            // SQL execution is routed to JS DuckDB-WASM via the Pyodide FFI bridge.
            try {
                await micropip.install(['ibis-framework', 'pandas', 'pyarrow', 'plotly'], installKwargs);
            } catch (micropipError) {
                console.warn('Micropip failed to install from index. Depending on environment, wheels may need manual caching.', micropipError);
                throw micropipError;
            }

            console.debug('WebAssembly runtime initialized successfully!');

            // Step 2: Initialize DuckDB-WASM
            this._onProgress('duckdb');
            await duckdbService.initialize();

            // Step 3: Pre-warm Python environment
            this._onProgress('bridge');
            await this._preWarmEnvironment();

            this.isInitializing = false;
            return this.pyodide;
        } catch (error) {
            console.error('Failed to initialize Pyodide:', error);
            this.isInitializing = false;
            this.initializationPromise = null;
            throw error;
        }
    }

    /**
     * Injects a Python bridge class that makes ibis route SQL to JS DuckDB-WASM.
     * 
     * How it works:
     * 1. Python ibis builds expression trees → compiles to SQL
     * 2. At .execute() time, ibis calls self.con.execute(sql)
     * 3. Our DuckDBProxy replaces self.con and forwards SQL to JS via Pyodide FFI
     * 4. JS DuckDB-WASM executes the query against lazily-loaded data
     * 5. Results come back as JSON → Python converts to pandas DataFrame
     */
    async _preWarmEnvironment() {
        if (!this.pyodide) return;
        try {
            console.debug('Pre-warming Pyodide environment and installing DuckDB bridge...');
            const prewarmScript = `
import pandas as pd
import pyarrow as pa
from pyodide.ffi import to_js
import asyncio

# ─────────────────────────────────────────────────────────────────────────────
# DUCKDB-WASM BRIDGE
# ─────────────────────────────────────────────────────────────────────────────
# Provides a global query() function that sends SQL to the JS DuckDB-WASM
# instance (where user data is loaded lazily via registerFileHandle) and
# returns results as pandas DataFrames.
#
# Since JS DuckDB-WASM query() is async, we use Pyodide's JsProxy.to_py()
# which automatically awaits Promises when called from async Python code.
# User code runs via runPythonAsync, so top-level await is supported.
# ─────────────────────────────────────────────────────────────────────────────

async def query(sql):
    """Execute SQL against DuckDB-WASM and return a pandas DataFrame.
    
    Since this is async, use it with await:
        df = await query("SELECT * FROM my_table LIMIT 10")
        print(df)
    """
    from js import _duckdb_query
    try:
        # _duckdb_query is async JS — calling it returns a JsProxy wrapping a Promise
        js_promise = _duckdb_query(sql)
        # Await the JS Promise from Python
        js_result = await js_promise
    except Exception as exc:
        sql_text = str(sql or "").strip().replace("\\n", " ")
        if len(sql_text) > 240:
            sql_text = sql_text[:240] + "..."
        raise RuntimeError(
            "DuckDB query failed: "
            + str(exc)
            + " | SQL: "
            + sql_text
            + " | Tip: if the query divides values, use NULLIF(denominator, 0)."
        ) from exc
    # Convert JS proxy to Python list of dicts
    rows = js_result.to_py() if hasattr(js_result, 'to_py') else list(js_result)
    return pd.DataFrame(rows)

# Make query() available as a builtin so AI-generated code can use it directly
import builtins
builtins.query = query

print("DuckDB-WASM bridge installed. Use: df = await query('SELECT ...')")
print("Pyodide pre-warming complete.")
`;
            await this.pyodide.runPythonAsync(prewarmScript);
            console.debug('Environment pre-warming successful.');
        } catch (e) {
            console.warn('Pre-warming failed (non-fatal):', e);
        }
    }

    /**
     * Restores Wasm state if the user refreshed the page.
     * Runs the historical code snippets accumulated in this session.
     */
    async restoreState(historicalCodeBlocks) {
        if (!this.pyodide) {
            await this.initialize();
        }

        if (!historicalCodeBlocks || historicalCodeBlocks.length === 0) {
            return;
        }

        console.debug('Restoring Pyodide state from history...');
        try {
            const fullHistoricalScript = historicalCodeBlocks.join('\n\n');
            await this.pyodide.runPythonAsync(fullHistoricalScript);
            this.accumulatedCode = fullHistoricalScript;
            console.debug('State restored successfully.');
        } catch (error) {
            console.error('Error restoring Pyodide state:', error);
            // If history restoration fails, the state might be corrupt, 
            // but we shouldn't necessarily crash the whole app.
        }
    }

    /**
     * Executes a Python code snippet.
     * Maintains state inside the Wasm memory.
     * 
     * @param {string} code - The Python snippet to execute.
     * @param {boolean} isDiff - Whether this is a partial run (diff) or a completely new script.
     */
    async executePython(code) {
        if (!this.pyodide) {
            await this.initialize();
        }

        try {
            console.debug('Executing Python snippet...');
            await ensureExecutionTableReady();

            // Standardize the code (e.g., catching final expression output natively in Pyodide REPL style)
            // Usually, just running it works if the script explicitly prints or if we capture the last expression.

            // To capture printed output:
            let stdout = [];
            let stderr = [];
            this.pyodide.setStdout({ batched: (str) => stdout.push(str) });
            this.pyodide.setStderr({ batched: (str) => stderr.push(str) });

            // Run the code
            const result = await this.pyodide.runPythonAsync(code);

            // Append strictly to our running tracker so we can restore on refresh
            this.accumulatedCode += '\n\n' + code;

            // Extract result value if it's a Pyodide foreign proxy (e.g. Pandas DataFrame)
            let finalResult = result;
            let resultType = typeof result;

            if (result && typeof result === 'object' && typeof result.toJs === 'function') {
                resultType = result.type || 'PyProxy';
                try {
                    finalResult = result.toJs({ dict_converter: Object.fromEntries });
                } catch (e) {
                    finalResult = result.toString();
                }
                result.destroy(); // Prevent memory leaks
            }

            return {
                success: true,
                result: finalResult,
                resultType: resultType,
                stdout: stdout.join('\n'),
                stderr: stderr.join('\n')
            };

        } catch (error) {
            console.error('Python execution error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Utility to clear Wasm state and accumulated variables
     */
    resetRuntime() {
        this.pyodide = null;
        this.initializationPromise = null;
        this.accumulatedCode = '';
    }
}

export const pyodideService = new PyodideService();
export default pyodideService;
