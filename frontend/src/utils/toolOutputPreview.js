const MAX_TEXT_CHARS = 4000
const MAX_RAW_JSON_CHARS = 6000
const MAX_TABLE_ROWS = 12
const MAX_TABLE_COLUMNS = 8

function asText(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}

function truncateText(text, max = MAX_TEXT_CHARS) {
  const value = String(text || '')
  if (value.length <= max) return { text: value, truncated: false }
  return { text: `${value.slice(0, max).trimEnd()}\n...`, truncated: true }
}

function looksLikeMarkdownTable(text) {
  const lines = String(text || '').trim().split(/\r?\n/).filter((line) => line.trim())
  if (lines.length < 2) return false
  const header = lines[0]
  const divider = lines[1]
  return header.includes('|') && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(divider)
}

function looksLikeSql(text) {
  return /^\s*(select|with|insert|update|delete|create|alter|drop|pragma|explain)\b/i.test(text)
}

function looksLikePython(text) {
  return /^\s*(import\s+|from\s+|def\s+|class\s+|print\(|if __name__|for\s+\w+\s+in|while\s+|try:|with\s+)/im.test(text)
    || /\b(pd|np|plt|duckdb|conn)\./.test(text)
}

function looksLikeBash(text) {
  return /^\s*(\$|uv\s+|python3?\s+|pip\s+|npm\s+|pnpm\s+|yarn\s+|git\s+|curl\s+|cd\s+|ls\s+|cat\s+|rg\s+|grep\s+|bash\s+)/im.test(text)
}

function classifyTextOutput(text, fallbackKind = 'logs') {
  const raw = String(text || '').trim()
  if (!raw) {
    return { kind: 'empty', text: '', truncated: false }
  }
  const { text: displayText, truncated } = truncateText(raw)
  if (looksLikeMarkdownTable(raw) || /```/.test(raw)) {
    return { kind: 'markdown', text: displayText, truncated }
  }
  if (looksLikeSql(raw)) {
    return { kind: 'code-sql', text: displayText, language: 'sql', truncated }
  }
  if (looksLikePython(raw)) {
    return { kind: 'code-python', text: displayText, language: 'python', truncated }
  }
  if (looksLikeBash(raw)) {
    return { kind: 'code-bash', text: displayText, language: 'bash', truncated }
  }
  return { kind: fallbackKind, text: displayText, truncated }
}

function normalizeColumns(rawColumns) {
  if (!Array.isArray(rawColumns)) return []
  return rawColumns
    .map((column) => {
      if (typeof column === 'string' || typeof column === 'number') return String(column)
      if (column && typeof column === 'object') {
        return String(column.name || column.field || column.key || column.column || '').trim()
      }
      return ''
    })
    .filter(Boolean)
    .slice(0, MAX_TABLE_COLUMNS)
}

function normalizeRows(rawRows, columns) {
  if (!Array.isArray(rawRows)) return []
  return rawRows.slice(0, MAX_TABLE_ROWS).map((row) => {
    if (Array.isArray(row)) {
      return columns.map((_, index) => asText(row[index]))
    }
    if (row && typeof row === 'object') {
      return columns.map((column) => asText(row[column]))
    }
    return [asText(row)]
  })
}

function tablePreviewFromObject(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
  const rawRows = (
    Array.isArray(payload.rows) ? payload.rows
      : Array.isArray(payload.data) ? payload.data
        : Array.isArray(payload.preview_rows) ? payload.preview_rows
          : []
  )
  if (!rawRows.length) return null
  let columns = normalizeColumns(payload.columns || payload.schema)
  if (!columns.length && rawRows[0] && typeof rawRows[0] === 'object' && !Array.isArray(rawRows[0])) {
    columns = Object.keys(rawRows[0]).slice(0, MAX_TABLE_COLUMNS)
  }
  if (!columns.length && Array.isArray(rawRows[0])) {
    columns = rawRows[0].map((_, index) => `Column ${index + 1}`).slice(0, MAX_TABLE_COLUMNS)
  }
  if (!columns.length) return null
  return {
    kind: 'table',
    columns,
    rows: normalizeRows(rawRows, columns),
    truncated: rawRows.length > MAX_TABLE_ROWS || columns.length < normalizeColumns(payload.columns || payload.schema).length,
    rowCount: Number.isFinite(Number(payload.row_count)) ? Number(payload.row_count) : rawRows.length,
  }
}

function jsonPreview(payload) {
  let raw = ''
  try {
    raw = JSON.stringify(payload, null, 2)
  } catch (_error) {
    raw = String(payload || '')
  }
  const { text, truncated } = truncateText(raw, MAX_RAW_JSON_CHARS)
  const summary = Object.entries(payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {})
    .slice(0, 4)
    .map(([key, value]) => {
      const rendered = asText(value) || (Array.isArray(value) ? `${value.length} items` : typeof value)
      return `${key}: ${String(rendered).slice(0, 80)}`
    })
  return { kind: 'json', text, summary, truncated }
}

export function buildToolOutputPreview(activity = {}) {
  const payload = activity?.output
  const status = String(activity?.status || '').trim().toLowerCase()
  if (payload === null || payload === undefined) {
    return { kind: 'empty', text: '', truncated: false }
  }
  if (typeof payload === 'string' || typeof payload === 'number' || typeof payload === 'boolean') {
    return classifyTextOutput(payload, status === 'error' ? 'logs' : 'markdown')
  }
  if (Array.isArray(payload)) {
    return jsonPreview(payload)
  }
  if (payload && typeof payload === 'object') {
    const table = tablePreviewFromObject(payload)
    if (table) return table

    const errorText = asText(payload.error || payload.stderr || payload.traceback)
    if (errorText) return { ...classifyTextOutput(errorText, 'logs'), error: true }

    const codeText = asText(payload.code || payload.command || payload.sql || payload.query)
    if (codeText) return classifyTextOutput(codeText, 'logs')

    const stdoutText = asText(payload.stdout || payload.output || payload.result_preview || payload.message)
    if (stdoutText) return classifyTextOutput(stdoutText, 'logs')
  }
  return jsonPreview(payload)
}

export function toolOutputHasRenderableContent(activity = {}) {
  return buildToolOutputPreview(activity).kind !== 'empty'
}
