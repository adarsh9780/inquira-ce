function asArray(value) {
  return Array.isArray(value) ? value : []
}

function clean(value) {
  return String(value || '').trim()
}

function resultName(item, fallback) {
  return clean(
    item?.display_name
    || item?.logical_name
    || item?.name
    || item?.data?.display_name
    || item?.data?.logical_name
    || fallback,
  )
}

function scalarOutputIdentity(item, index = 0) {
  const artifactId = clean(item?.artifact_id)
  const runId = clean(item?.runId || item?.run_id)
  const name = resultName(item, `scalar_${index + 1}`)
  return artifactId || [runId, name, index + 1].filter(Boolean).join(':')
}

function normalizeScalarOutput(item, index = 0) {
  const raw = item && typeof item === 'object' ? item : { value: item }
  const value = Object.prototype.hasOwnProperty.call(raw, 'display_value')
    ? raw.display_value
    : (Object.prototype.hasOwnProperty.call(raw, 'value') ? raw.value : raw?.payload?.value)
  return {
    id: scalarOutputIdentity(raw, index),
    name: resultName(raw, `Scalar ${index + 1}`),
    value,
    type: clean(raw?.result_type || raw?.type),
    runId: clean(raw?.runId || raw?.run_id),
    createdAt: clean(raw?.createdAt || raw?.created_at),
  }
}

function executionTimestamp(item) {
  const raw = clean(item?.createdAt || item?.created_at)
  const parsed = raw ? Date.parse(raw) : Number.NaN
  return Number.isFinite(parsed) ? parsed : 0
}

function isUserExecutionEntry(entry) {
  const origin = clean(entry?.origin).toLowerCase()
  if (origin) return origin === 'user'
  return ['code run', 'selection run'].includes(clean(entry?.label).toLowerCase())
}

function normalizeStructuredOutput(item, index, kind, runId) {
  const raw = item && typeof item === 'object' ? item : { data: item }
  const name = resultName(raw, `${kind === 'table' ? 'Table' : 'Chart'} ${index + 1}`)
  const artifactId = clean(raw?.data?.artifact_id || raw?.artifact_id)
  return {
    ...raw,
    id: artifactId || `${kind}:${runId || 'run'}:${index + 1}`,
    name,
    runId: clean(raw?.runId || raw?.run_id) || runId,
    data: raw?.data ?? raw,
  }
}

export function buildUserRunItems({
  terminalEntries = [],
  conversationId = '',
} = {}) {
  const activeConversationId = clean(conversationId)
  const executions = asArray(terminalEntries)
    .filter((entry) => entry?.kind === 'output' && entry?.source === 'analysis')
    .filter(isUserExecutionEntry)
    .filter((entry) => {
      const entryConversationId = clean(entry?.conversationId)
      return !activeConversationId || !entryConversationId || entryConversationId === activeConversationId
    })
    .map((entry, entryIndex) => {
      const runId = clean(entry?.runId)
      const stdout = String(entry?.stdout || '')
      const stderr = String(entry?.stderr || '')
      return {
        id: `execution:${clean(entry?.id) || entryIndex + 1}`,
        entryId: clean(entry?.id),
        runId,
        label: clean(entry?.label) || 'Code run',
        status: clean(entry?.status) || (stderr.trim() ? 'error' : 'success'),
        code: String(entry?.command || ''),
        stdout,
        stderr,
        scalarOutputs: asArray(entry?.scalarOutputs).map(normalizeScalarOutput),
        tableOutputs: asArray(entry?.tableOutputs)
          .map((item, index) => normalizeStructuredOutput(item, index, 'table', runId)),
        chartOutputs: asArray(entry?.chartOutputs)
          .map((item, index) => normalizeStructuredOutput(item, index, 'chart', runId)),
        durationMs: Number.isFinite(Number(entry?.durationMs)) ? Number(entry.durationMs) : null,
        createdAt: clean(entry?.createdAt),
        truncated: Boolean(entry?.truncated),
        sequence: entryIndex + 1,
      }
    })

  return executions.sort((left, right) => {
    const timestampDelta = executionTimestamp(right) - executionTimestamp(left)
    if (timestampDelta !== 0) return timestampDelta
    return Number(right.sequence || 0) - Number(left.sequence || 0)
  })
}
