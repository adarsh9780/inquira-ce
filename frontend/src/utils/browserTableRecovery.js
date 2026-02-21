export async function ensureBrowserTableReady(options = {}) {
  const {
    expectedTableName,
    duckdb = null,
    canPersistHandles = null,
    getHandleRecord = null,
    clearHandle = null,
    isStaleHandleError = null
  } = options

  const resolvedDuckdb = duckdb || (await import('../services/duckdbService.js')).duckdbService
  const fileHandleStore = (getHandleRecord && clearHandle)
    ? null
    : await import('../services/fileHandleStore.js')
  const fileHandleSupport = (canPersistHandles !== null && isStaleHandleError)
    ? null
    : await import('./fileHandleSupport.js')

  const resolvedCanPersistHandles =
    canPersistHandles !== null
      ? canPersistHandles
      : fileHandleSupport.supportsPersistentFileHandles()
  const resolvedGetHandleRecord = getHandleRecord || fileHandleStore.getActiveFileHandleRecord
  const resolvedClearHandle = clearHandle || fileHandleStore.clearActiveFileHandle
  const resolvedIsStaleHandleError = isStaleHandleError || fileHandleSupport.isLikelyStaleHandleError

  if (!expectedTableName || !String(expectedTableName).trim()) {
    throw new Error('No active dataset table found. Please select your data file first.')
  }

  const currentTables = await resolvedDuckdb.getTableNames()
  if (currentTables.includes(expectedTableName)) {
    return { tableName: expectedTableName, recovered: false }
  }

  if (!resolvedCanPersistHandles) {
    throw new Error('Dataset is not loaded in this browser session. Please reselect your data file in the Data tab.')
  }

  try {
    const record = await resolvedGetHandleRecord()
    const handle = record?.handle
    if (!handle) {
      throw new Error('No saved data file handle found. Please reselect your data file in the Data tab.')
    }

    let permission = 'prompt'
    if (typeof handle.queryPermission === 'function') {
      permission = await handle.queryPermission({ mode: 'read' })
    }
    if (permission !== 'granted' && typeof handle.requestPermission === 'function') {
      permission = await handle.requestPermission({ mode: 'read' })
    }
    if (permission !== 'granted') {
      throw new Error('Data file permission was not granted. Please reselect your data file in the Data tab.')
    }

    const file = await handle.getFile()
    const { tableName, columns } = await resolvedDuckdb.ingestFile(file)
    return { tableName, columns, fileName: file?.name || '', recovered: true }
  } catch (error) {
    if (resolvedIsStaleHandleError(error)) {
      await resolvedClearHandle()
      throw new Error('Saved file reference is stale. Please reselect your data file in the Data tab.')
    }
    throw error
  }
}
