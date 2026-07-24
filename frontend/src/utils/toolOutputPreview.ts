const MAX_TEXT_CHARS = 4000
const MAX_RAW_JSON_CHARS = 6000
const MAX_TABLE_ROWS = 12
const MAX_TABLE_COLUMNS = 8

type RecordValue = Record<string, unknown>

export interface ToolOutputPreview {
  kind: string
  text?: string
  truncated: boolean
  language?: string
  columns?: string[]
  rows?: string[][]
  rowCount?: number
  summary?: string[]
  error?: boolean
}

function asRecord(value: unknown): RecordValue | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as RecordValue
    : null
}

function asText(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}

function truncateText(text: unknown, max = MAX_TEXT_CHARS): { text: string; truncated: boolean } {
  const value = String(text || '')
  if (value.length <= max) return { text: value, truncated: false }
  return { text: `${value.slice(0, max).trimEnd()}\n...`, truncated: true }
}

function looksLikeMarkdownTable(text: unknown): boolean {
  const lines = String(text || '').trim().split(/\r?\n/).filter((line) => line.trim())
  if (lines.length < 2) return false
  const header = lines[0]
  const divider = lines[1]
  return header.includes('|') && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(divider)
}

function looksLikeSql(text: unknown): boolean {
  return /^\s*(select|with|insert|update|delete|create|alter|drop|pragma|explain)\b/i.test(String(text || ''))
}

function looksLikePython(text: unknown): boolean {
  const value = String(text || '')
  return /^\s*(import\s+|from\s+|def\s+|class\s+|print\(|if __name__|for\s+\w+\s+in|while\s+|try:|with\s+)/im.test(value)
    || /\b(pd|np|plt|duckdb|conn)\./.test(value)
}

function looksLikeBash(text: unknown): boolean {
  return /^\s*(\$|uv\s+|python3?\s+|pip\s+|npm\s+|pnpm\s+|yarn\s+|git\s+|curl\s+|cd\s+|ls\s+|cat\s+|rg\s+|grep\s+|bash\s+)/im.test(String(text || ''))
}

function classifyTextOutput(text: unknown, fallbackKind = 'logs'): ToolOutputPreview {
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

function normalizeColumns(rawColumns: unknown): string[] {
  if (!Array.isArray(rawColumns)) return []
  return rawColumns
    .map((column) => {
      if (typeof column === 'string' || typeof column === 'number') return String(column)
      const record = asRecord(column)
      if (record) {
        return String(record.name || record.field || record.key || record.column || '').trim()
      }
      return ''
    })
    .filter(Boolean)
    .slice(0, MAX_TABLE_COLUMNS)
}

function normalizeRows(rawRows: unknown, columns: string[]): string[][] {
  if (!Array.isArray(rawRows)) return []
  return rawRows.slice(0, MAX_TABLE_ROWS).map((row) => {
    if (Array.isArray(row)) {
      return columns.map((_, index) => asText(row[index]))
    }
    const record = asRecord(row)
    if (record) {
      return columns.map((column) => asText(record[column]))
    }
    return [asText(row)]
  })
}

function tablePreviewFromObject(payload: unknown): ToolOutputPreview | null {
  const record = asRecord(payload)
  if (!record) return null
  const rawRows = (
    Array.isArray(record.rows) ? record.rows
      : Array.isArray(record.data) ? record.data
        : Array.isArray(record.preview_rows) ? record.preview_rows
          : []
  )
  if (!rawRows.length) return null
  let columns = normalizeColumns(record.columns || record.schema)
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
    truncated: rawRows.length > MAX_TABLE_ROWS || columns.length < normalizeColumns(record.columns || record.schema).length,
    rowCount: Number.isFinite(Number(record.row_count)) ? Number(record.row_count) : rawRows.length,
  }
}

function jsonPreview(payload: unknown): ToolOutputPreview {
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

export function buildToolOutputPreview(activity: unknown = {}): ToolOutputPreview {
  const record = asRecord(activity) || {}
  const payload = record.output
  const status = String(record.status || '').trim().toLowerCase()
  if (payload === null || payload === undefined) {
    return { kind: 'empty', text: '', truncated: false }
  }
  if (typeof payload === 'string' || typeof payload === 'number' || typeof payload === 'boolean') {
    return classifyTextOutput(payload, status === 'error' ? 'logs' : 'markdown')
  }
  if (Array.isArray(payload)) {
    return jsonPreview(payload)
  }
  const payloadRecord = asRecord(payload)
  if (payloadRecord) {
    const table = tablePreviewFromObject(payload)
    if (table) return table

    const errorText = asText(payloadRecord.error || payloadRecord.stderr || payloadRecord.traceback)
    if (errorText) return { ...classifyTextOutput(errorText, 'logs'), error: true }

    const codeText = asText(payloadRecord.code || payloadRecord.command || payloadRecord.sql || payloadRecord.query)
    if (codeText) return classifyTextOutput(codeText, 'logs')

    const stdoutText = asText(
      payloadRecord.stdout
      || payloadRecord.output
      || payloadRecord.result_preview
      || payloadRecord.message,
    )
    if (stdoutText) return classifyTextOutput(stdoutText, 'logs')
  }
  return jsonPreview(payload)
}

export function toolOutputHasRenderableContent(activity: unknown = {}): boolean {
  return buildToolOutputPreview(activity).kind !== 'empty'
}
