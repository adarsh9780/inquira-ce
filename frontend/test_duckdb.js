const { loadPyodide } = require('pyodide');

async function main() {
  const pyodide = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/' });
  await pyodide.loadPackage('micropip');
  const micropip = pyodide.pyimport('micropip');
  await micropip.install('duckdb');
  console.log("DuckDB installed. Now trying to import it.");
  await pyodide.runPythonAsync(`
    import duckdb
    print(duckdb.__version__)
  `);
}

main().catch(console.error);
