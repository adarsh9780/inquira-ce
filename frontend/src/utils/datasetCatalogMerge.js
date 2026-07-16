import { buildBrowserDataPath, inferTableNameFromDataPath } from './chatBootstrap.js'

function normalizeDatasetRecord(ds) {
  const tableName = (ds?.table_name || inferTableNameFromDataPath(ds?.file_path || '')).trim()
  if (!tableName) return null

  const filePath = (typeof ds?.file_path === 'string' && ds.file_path.trim())
    ? ds.file_path.trim()
    : buildBrowserDataPath(tableName)

  return {
    ...ds,
    table_name: tableName,
    file_path: filePath
  }
}

export function mergeDatasetSources({
  catalogDatasets = [],
  runtimeTables = [],
  currentDataPath = ''
} = {}) {
  const byTableName = new Map()

  for (const raw of Array.isArray(catalogDatasets) ? catalogDatasets : []) {
    const normalized = normalizeDatasetRecord(raw)
    if (!normalized) continue
    byTableName.set(normalized.table_name, normalized)
  }

  for (const tableNameRaw of Array.isArray(runtimeTables) ? runtimeTables : []) {
    const tableName = String(tableNameRaw || '').trim()
    if (!tableName) continue
    if (!byTableName.has(tableName)) {
      byTableName.set(tableName, {
        table_name: tableName,
        file_path: buildBrowserDataPath(tableName),
        source: 'browser-runtime'
      })
    }
  }

  const inferredCurrentTable = inferTableNameFromDataPath(currentDataPath)
  if (inferredCurrentTable && !byTableName.has(inferredCurrentTable)) {
    byTableName.set(inferredCurrentTable, {
      table_name: inferredCurrentTable,
      file_path: buildBrowserDataPath(inferredCurrentTable),
      source: 'active-state'
    })
  }

  return Array.from(byTableName.values())
}
