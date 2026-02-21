export function buildBrowserDataPath(tableName) {
  const normalized = typeof tableName === 'string' ? tableName.trim() : ''
  if (!normalized) return ''
  return `browser://${normalized}`
}

export function hasUsableIngestedColumns(columns) {
  return Array.isArray(columns) && columns.some((col) => typeof col?.name === 'string' && col.name.trim())
}
