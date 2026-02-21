import { buildBrowserDataPath, inferTableNameFromDataPath } from './chatBootstrap.js'
import { ensureBrowserTableReady } from './browserTableRecovery.js'

export async function ensureExecutionTableReady(options = {}) {
  const {
    appStore: providedStore = null,
    ensureTableReady = ensureBrowserTableReady,
    duckdb: providedDuckdb = null
  } = options

  let appStore = providedStore
  if (!appStore) {
    const { useAppStore } = await import('../stores/appStore.js')
    appStore = useAppStore()
  }

  const expectedTableName = (
    appStore.ingestedTableName ||
    inferTableNameFromDataPath(appStore.schemaFileId) ||
    inferTableNameFromDataPath(appStore.dataFilePath)
  ).trim()

  if (!expectedTableName) return null

  const resolvedDuckdb = providedDuckdb || (await import('../services/duckdbService.js')).duckdbService
  const tableHealth = await ensureTableReady({
    expectedTableName,
    duckdb: resolvedDuckdb
  })

  if (tableHealth?.tableName) {
    appStore.setIngestedTableName(tableHealth.tableName)
    appStore.setSchemaFileId(buildBrowserDataPath(tableHealth.tableName))
    appStore.setDataFilePath(buildBrowserDataPath(tableHealth.tableName))
  }

  if (Array.isArray(tableHealth?.columns) && tableHealth.columns.length > 0) {
    appStore.setIngestedColumns(tableHealth.columns)
  }

  return tableHealth
}
