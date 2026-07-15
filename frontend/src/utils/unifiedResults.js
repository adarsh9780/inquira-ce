const RESULT_KIND_LABELS = {
  table: 'Table',
  chart: 'Chart',
  log: 'Run output',
  scalar: 'Scalar',
}

function asArray(value) {
  return Array.isArray(value) ? value : []
}

function clean(value) {
  return String(value || '').trim()
}

function itemTimestamp(item) {
  const raw = clean(item?.createdAt || item?.created_at || item?.data?.created_at)
  const parsed = raw ? Date.parse(raw) : Number.NaN
  return Number.isFinite(parsed) ? parsed : 0
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

export function executionLogResultId(entryId) {
  const normalized = clean(entryId)
  return normalized ? `log:${normalized}` : ''
}

export function dataframeResultIdentity(item, index = 0) {
  const artifactId = clean(item?.data?.artifact_id || item?.artifact_id) || `live-dataframe-${index + 1}`
  return {
    artifactId,
    resultId: `table:${artifactId}`,
  }
}

export function figureResultIdentity(item, index = 0) {
  const artifactId = clean(item?.artifact_id || item?.data?.artifact_id) || `live-figure-${index + 1}`
  return {
    artifactId,
    resultId: `chart:${artifactId}`,
  }
}

function scalarResultIdentity(item, index = 0) {
  const artifactId = clean(item?.artifact_id)
  const fallbackKey = [clean(item?.runId || item?.run_id), resultName(item, `scalar_${index + 1}`), index + 1]
    .filter(Boolean)
    .join(':')
  return {
    artifactId,
    resultId: `scalar:${artifactId || fallbackKey}`,
  }
}

function makeArtifactResult({ item, index, kind, identity }) {
  const label = resultName(item, `${RESULT_KIND_LABELS[kind]} ${index + 1}`)
  return {
    id: identity.resultId,
    kind,
    label,
    optionLabel: `${label} · ${RESULT_KIND_LABELS[kind]}`,
    artifactId: identity.artifactId,
    runId: clean(item?.runId || item?.run_id || item?.data?.runId || item?.data?.run_id),
    status: clean(item?.status) || 'success',
    createdAt: clean(item?.createdAt || item?.created_at || item?.data?.created_at),
    raw: item,
  }
}

function makeTurnArtifactResult(artifact, index) {
  const artifactKind = clean(artifact?.kind).toLowerCase()
  const kind = artifactKind === 'dataframe'
    ? 'table'
    : (artifactKind === 'figure' ? 'chart' : (artifactKind === 'scalar' ? 'scalar' : ''))
  if (!kind) return null
  const artifactId = clean(artifact?.artifact_id)
  if (!artifactId) return null
  const label = resultName(artifact, `${RESULT_KIND_LABELS[kind]} ${index + 1}`)
  return {
    id: `${kind}:${artifactId}`,
    kind,
    label,
    optionLabel: `${label} · ${RESULT_KIND_LABELS[kind]}`,
    artifactId,
    runId: clean(artifact?.runId || artifact?.run_id),
    status: clean(artifact?.status) || 'success',
    createdAt: clean(artifact?.createdAt || artifact?.created_at),
    raw: artifact,
  }
}

export function buildUnifiedResultItems({
  dataframes = [],
  figures = [],
  scalars = [],
  terminalEntries = [],
  activeTurnArtifacts = [],
} = {}) {
  const results = []
  const seen = new Set()
  let sequence = 0

  function append(result) {
    if (!result?.id || seen.has(result.id)) return
    seen.add(result.id)
    results.push({ ...result, sequence: sequence += 1 })
  }

  asArray(dataframes).forEach((item, index) => {
    append(makeArtifactResult({
      item,
      index,
      kind: 'table',
      identity: dataframeResultIdentity(item, index),
    }))
  })

  asArray(figures).forEach((item, index) => {
    append(makeArtifactResult({
      item,
      index,
      kind: 'chart',
      identity: figureResultIdentity(item, index),
    }))
  })

  asArray(scalars).forEach((item, index) => {
    append(makeArtifactResult({
      item,
      index,
      kind: 'scalar',
      identity: scalarResultIdentity(item, index),
    }))
  })

  asArray(activeTurnArtifacts).forEach((artifact, index) => {
    append(makeTurnArtifactResult(artifact, index))
  })

  asArray(terminalEntries)
    .filter((entry) => entry?.kind === 'output' && entry?.source === 'analysis')
    .forEach((entry, index) => {
      const id = executionLogResultId(entry?.id)
      if (!id) return
      const status = clean(entry?.status) || (clean(entry?.stderr) ? 'error' : 'success')
      const label = clean(entry?.label) || `Run ${index + 1}`
      append({
        id,
        kind: 'log',
        label,
        optionLabel: `${label} · ${status === 'error' ? 'Error' : RESULT_KIND_LABELS.log}`,
        artifactId: '',
        runId: clean(entry?.runId),
        status,
        createdAt: clean(entry?.createdAt),
        raw: entry,
      })
    })

  return results.sort((left, right) => {
    const timestampDelta = itemTimestamp(right) - itemTimestamp(left)
    if (timestampDelta !== 0) return timestampDelta
    return Number(right.sequence || 0) - Number(left.sequence || 0)
  })
}

function normalizedResultKind(value) {
  const normalized = clean(value).toLowerCase()
  if (normalized === 'dataframe' || normalized === 'table') return 'table'
  if (normalized === 'figure' || normalized === 'chart') return 'chart'
  if (normalized === 'scalar') return 'scalar'
  if (normalized === 'log' || normalized === 'output' || normalized === 'text') return 'log'
  return ''
}

export function preferredExecutionResultId({
  items = [],
  runId = '',
  resultKind = '',
  resultName: explicitResultName = '',
  hasError = false,
  logEntryId = '',
  hasConsoleOutput = false,
} = {}) {
  const normalizedRunId = clean(runId)
  const candidates = asArray(items).filter((item) => !normalizedRunId || clean(item?.runId) === normalizedRunId)
  const logId = executionLogResultId(logEntryId)
  const logResult = candidates.find((item) => item.id === logId)

  if (hasError) return logResult?.id || logId

  const explicitName = clean(explicitResultName).toLowerCase()
  if (explicitName) {
    const named = candidates.find((item) => clean(item?.label).toLowerCase() === explicitName)
    if (named) return named.id
  }

  const preferredKind = normalizedResultKind(resultKind)
  if (preferredKind) {
    const typed = candidates.find((item) => item.kind === preferredKind)
    if (typed) return typed.id
  }

  for (const kind of ['chart', 'table', 'scalar']) {
    const artifact = candidates.find((item) => item.kind === kind)
    if (artifact) return artifact.id
  }

  if (hasConsoleOutput && logResult) return logResult.id
  return logResult?.id || candidates[0]?.id || ''
}

export function resultPaneForKind(kind) {
  if (kind === 'table') return 'table'
  if (kind === 'chart') return 'figure'
  return 'output'
}
