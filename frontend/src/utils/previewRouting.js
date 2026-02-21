export function isBrowserDataPath(dataPath) {
  return typeof dataPath === 'string' && dataPath.startsWith('browser://')
}

export function buildPreviewSql(tableName, sampleType = 'random', sampleSize = 100) {
  const limit = Number.isFinite(sampleSize) ? Math.max(1, Math.floor(sampleSize)) : 100
  if (sampleType === 'first') {
    return `SELECT * FROM ${tableName} LIMIT ${limit}`
  }
  return `SELECT * FROM ${tableName} ORDER BY RANDOM() LIMIT ${limit}`
}
