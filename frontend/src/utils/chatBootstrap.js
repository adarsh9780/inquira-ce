export function buildBrowserDataPath(tableName) {
  const normalized = typeof tableName === 'string' ? tableName.trim() : ''
  if (!normalized) return ''
  return `browser://${normalized}`
}

export function inferTableNameFromDataPath(dataPath) {
  let value = typeof dataPath === 'string' ? dataPath.trim() : ''
  if (!value) return ''

  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1).trim()
  }

  if (value.startsWith('/browser:/')) {
    value = value.slice(1)
  }

  if (value.startsWith('browser://')) {
    return value.slice('browser://'.length).trim()
  }

  if (value.startsWith('browser:/')) {
    return value.slice('browser:/'.length).trim()
  }

  const base = value.split('/').pop() || ''
  return base.replace(/\.[^.]+$/, '').trim()
}

export function hasUsableIngestedColumns(columns) {
  return Array.isArray(columns) && columns.some((col) => typeof col?.name === 'string' && col.name.trim())
}
