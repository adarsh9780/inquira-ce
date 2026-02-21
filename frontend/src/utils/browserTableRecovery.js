export async function ensureBrowserTableReady(options = {}) {
  const {
    expectedTableName,
    duckdb = null,
    canPersistHandles = null,
    getHandleRecord = null,
    clearHandle = null,
    isStaleHandleError = null,
    recoverFromRemote = null
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
  const resolvedRecoverFromRemote = recoverFromRemote || defaultRecoverFromRemote

  if (!expectedTableName || !String(expectedTableName).trim()) {
    throw new Error('No active dataset table found. Please select your data file first.')
  }

  const currentTables = await resolvedDuckdb.getTableNames()
  if (currentTables.includes(expectedTableName)) {
    return { tableName: expectedTableName, recovered: false }
  }

  let localRecoveryError = null
  try {
    if (!resolvedCanPersistHandles) {
      throw new Error('Dataset is not loaded in this browser session. Please reselect your data file in the Data tab.')
    }

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
      localRecoveryError = new Error('Saved file reference is stale. Please reselect your data file in the Data tab.')
    } else {
      localRecoveryError = error
    }
  }

  try {
    const remoteResult = await resolvedRecoverFromRemote({
      expectedTableName,
      duckdb: resolvedDuckdb
    })
    if (remoteResult?.tableName) {
      return { ...remoteResult, recovered: true }
    }
  } catch (_remoteError) {
    // Prefer local recovery errors for clearer user guidance.
  }

  if (localRecoveryError) {
    throw localRecoveryError
  }

  throw new Error('Dataset could not be loaded in this browser session. Please reselect your data file in the Data tab.')
}

async function defaultRecoverFromRemote({ expectedTableName, duckdb }) {
  if (!expectedTableName) {
    throw new Error('Missing table name for remote recovery.')
  }

  const { default: apiService } = await import('../services/apiService.js')
  const response = await apiService.listDatasets()
  const datasets = response?.datasets || response || []
  const dataset = datasets.find((ds) => ds?.table_name === expectedTableName)
  if (!dataset) {
    throw new Error('Dataset not found in backend catalog.')
  }

  const blob = await apiService.downloadDatasetBlob(expectedTableName)
  const fileName = inferFileNameFromPath(dataset.file_path, expectedTableName)
  const file = new File([blob], fileName, { type: blob?.type || 'application/octet-stream' })
  const { tableName, columns } = await duckdb.ingestFile(file)
  return { tableName, columns, fileName }
}

function inferFileNameFromPath(filePath, fallbackTableName) {
  const normalized = typeof filePath === 'string' ? filePath.trim() : ''
  if (normalized) {
    const parts = normalized.split(/[\\/]/)
    const base = parts[parts.length - 1]
    if (base) return base
  }
  return `${fallbackTableName}.csv`
}
