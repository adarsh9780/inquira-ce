type RecordValue = Record<string, unknown>

export interface ScalarRunOutput {
  id: string
  name: string
  value: unknown
  type: string
  runId: string
  createdAt: string
}

export interface StructuredRunOutput extends RecordValue {
  id: string
  name: string
  runId: string
  data: unknown
}

export interface UserRunItem {
  id: string
  entryId: string
  runId: string
  label: string
  status: string
  code: string
  stdout: string
  stderr: string
  scalarOutputs: ScalarRunOutput[]
  tableOutputs: StructuredRunOutput[]
  chartOutputs: StructuredRunOutput[]
  durationMs: number | null
  createdAt: string
  truncated: boolean
  sequence: number
}

export interface BuildUserRunItemsOptions {
  terminalEntries?: unknown[]
  conversationId?: unknown
}

function asRecord(value: unknown): RecordValue {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as RecordValue
    : {}
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function clean(value: unknown): string {
  return String(value || '').trim()
}

function resultName(itemValue: unknown, fallback: string): string {
  const item = asRecord(itemValue)
  const data = asRecord(item.data)
  return clean(
    item.display_name
    || item.logical_name
    || item.name
    || data.display_name
    || data.logical_name
    || fallback,
  )
}

function scalarOutputIdentity(itemValue: unknown, index = 0): string {
  const item = asRecord(itemValue)
  const artifactId = clean(item.artifact_id)
  const runId = clean(item.runId || item.run_id)
  const name = resultName(item, `scalar_${index + 1}`)
  return artifactId || [runId, name, index + 1].filter(Boolean).join(':')
}

function normalizeScalarOutput(item: unknown, index = 0): ScalarRunOutput {
  const raw = item && typeof item === 'object' && !Array.isArray(item)
    ? item as RecordValue
    : { value: item }
  const payload = asRecord(raw.payload)
  const value = Object.prototype.hasOwnProperty.call(raw, 'display_value')
    ? raw.display_value
    : (Object.prototype.hasOwnProperty.call(raw, 'value') ? raw.value : payload.value)
  return {
    id: scalarOutputIdentity(raw, index),
    name: resultName(raw, `Scalar ${index + 1}`),
    value,
    type: clean(raw.result_type || raw.type),
    runId: clean(raw.runId || raw.run_id),
    createdAt: clean(raw.createdAt || raw.created_at),
  }
}

function executionTimestamp(itemValue: unknown): number {
  const item = asRecord(itemValue)
  const raw = clean(item.createdAt || item.created_at)
  const parsed = raw ? Date.parse(raw) : Number.NaN
  return Number.isFinite(parsed) ? parsed : 0
}

function isUserExecutionEntry(entryValue: unknown): boolean {
  const entry = asRecord(entryValue)
  const origin = clean(entry.origin).toLowerCase()
  if (origin) return origin === 'user'
  return ['code run', 'selection run'].includes(clean(entry.label).toLowerCase())
}

function normalizeStructuredOutput(
  item: unknown,
  index: number,
  kind: 'table' | 'chart',
  runId: string,
): StructuredRunOutput {
  const raw = item && typeof item === 'object' && !Array.isArray(item)
    ? item as RecordValue
    : { data: item }
  const data = asRecord(raw.data)
  const name = resultName(raw, `${kind === 'table' ? 'Table' : 'Chart'} ${index + 1}`)
  const artifactId = clean(data.artifact_id || raw.artifact_id)
  return {
    ...raw,
    id: artifactId || `${kind}:${runId || 'run'}:${index + 1}`,
    name,
    runId: clean(raw.runId || raw.run_id) || runId,
    data: raw.data ?? raw,
  }
}

export function buildUserRunItems({
  terminalEntries = [],
  conversationId = '',
}: BuildUserRunItemsOptions = {}): UserRunItem[] {
  const activeConversationId = clean(conversationId)
  const executions = asArray(terminalEntries)
    .map(asRecord)
    .filter((entry) => entry.kind === 'output' && entry.source === 'analysis')
    .filter(isUserExecutionEntry)
    .filter((entry) => {
      const entryConversationId = clean(entry.conversationId)
      return !activeConversationId || !entryConversationId || entryConversationId === activeConversationId
    })
    .map((entry, entryIndex) => {
      const runId = clean(entry.runId)
      const stdout = String(entry.stdout || '')
      const stderr = String(entry.stderr || '')
      return {
        id: `execution:${clean(entry.id) || entryIndex + 1}`,
        entryId: clean(entry.id),
        runId,
        label: clean(entry.label) || 'Code run',
        status: clean(entry.status) || (stderr.trim() ? 'error' : 'success'),
        code: String(entry.command || ''),
        stdout,
        stderr,
        scalarOutputs: asArray(entry.scalarOutputs).map(normalizeScalarOutput),
        tableOutputs: asArray(entry.tableOutputs)
          .map((item, index) => normalizeStructuredOutput(item, index, 'table', runId)),
        chartOutputs: asArray(entry.chartOutputs)
          .map((item, index) => normalizeStructuredOutput(item, index, 'chart', runId)),
        durationMs: Number.isFinite(Number(entry.durationMs)) ? Number(entry.durationMs) : null,
        createdAt: clean(entry.createdAt),
        truncated: Boolean(entry.truncated),
        sequence: entryIndex + 1,
      }
    })

  return executions.sort((left, right) => {
    const timestampDelta = executionTimestamp(right) - executionTimestamp(left)
    if (timestampDelta !== 0) return timestampDelta
    return Number(right.sequence || 0) - Number(left.sequence || 0)
  })
}
