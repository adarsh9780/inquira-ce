import {
  normalizePlotlyFigure,
  type NormalizedPlotlyFigure,
} from './figurePayload.ts'

type RecordValue = Record<string, unknown>

interface NamedValue {
  name: string
  value: unknown
}

interface NamedData extends RecordValue {
  name: string
  data: unknown
}

interface FigureData extends RecordValue {
  name: string
  data: NormalizedPlotlyFigure
}

interface ScalarData extends RecordValue {
  name: string
  value: unknown
}

interface ParsedBucket {
  entries: NamedValue[]
  rawCount: number
  failed: number
}

interface ExecutionViewModelOptions {
  dataframeLine?: (count: number) => string
  figureLine?: (count: number) => string
  scalarLine?: (count: number) => string
  dataframeParseErrorLine?: string
  figureParseErrorLine?: string
  scalarParseErrorLine?: string
  successLine?: string
  includeVariableSummary?: boolean
  variableSummaryLine?: (counts: ExecutionCounts) => string
}

export interface ExecutionCounts {
  dataframes: number
  figures: number
  scalars: number
}

export interface ExecutionViewModel {
  output: string
  dataframes: NamedData[]
  figures: FigureData[]
  scalars: ScalarData[]
  counts: ExecutionCounts
}

function asRecord(value: unknown): RecordValue {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as RecordValue
    : {}
}

function parseObjectBucket(
  bucket: unknown,
  { parseJson = false }: { parseJson?: boolean } = {},
): ParsedBucket {
  if (!bucket || typeof bucket !== 'object' || Array.isArray(bucket)) {
    return { entries: [], rawCount: 0, failed: 0 }
  }

  let failed = 0
  const entries: NamedValue[] = []

  for (const [name, value] of Object.entries(bucket)) {
    try {
      const parsedValue = parseJson && typeof value === 'string' ? JSON.parse(value) : value
      entries.push({ name, value: parsedValue })
    } catch (_error) {
      failed += 1
    }
  }

  return { entries, rawCount: Object.keys(bucket).length, failed }
}

function dedupeByName<T extends { name: string }>(items: T[] = []): T[] {
  const seen = new Set<string>()
  return items.filter((item) => {
    const key = String(item.name || '').trim().toLowerCase()
    if (!key) return false
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function comparableNames(itemValue: unknown): string[] {
  const item = asRecord(itemValue)
  const data = asRecord(item.data)
  return [
    item.name,
    item.logical_name,
    item.display_name,
    data.logical_name,
    data.display_name,
  ]
    .map((value) => String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ''))
    .filter(Boolean)
}

function entriesMatch(left: unknown, right: unknown): boolean {
  const rightNames = new Set(comparableNames(right))
  return comparableNames(left).some((name) => rightNames.has(name))
}

function dataframeShape(value: unknown): { rows: RecordValue[]; columns: string[] } {
  if (Array.isArray(value)) {
    const rows = value.filter((row): row is RecordValue => (
      Boolean(row && typeof row === 'object' && !Array.isArray(row))
    ))
    return { rows, columns: rows[0] ? Object.keys(rows[0]) : [] }
  }
  const record = asRecord(value)
  if (Object.keys(record).length === 0) return { rows: [], columns: [] }
  const columns = Array.isArray(record.columns) ? record.columns.map(String) : []
  const rows = normalizePreviewRows(record.data ?? record.rows, columns)
  return { rows, columns: columns.length ? columns : (rows[0] ? Object.keys(rows[0]) : []) }
}

function mergeDataframeEntries(
  artifactEntries: NamedData[],
  parsedEntries: NamedData[],
): NamedData[] {
  const consumed = new Set<number>()
  const enrichedArtifacts = artifactEntries.map((artifact) => {
    const parsedIndex = parsedEntries.findIndex((entry, index) => !consumed.has(index) && entriesMatch(artifact, entry))
    if (parsedIndex < 0) return artifact
    consumed.add(parsedIndex)
    const parsed = parsedEntries[parsedIndex]
    const shape = dataframeShape(parsed.data)
    if (!shape.rows.length && !shape.columns.length) return artifact
    return {
      ...artifact,
      data: {
        ...asRecord(artifact.data),
        columns: shape.columns,
        data: shape.rows,
        row_count: Math.max(Number(asRecord(artifact.data).row_count || 0), shape.rows.length),
      },
    }
  })
  return dedupeByName([
    ...enrichedArtifacts,
    ...parsedEntries.filter((_entry, index) => !consumed.has(index)),
  ])
}

function normalizePreviewRows(rows: unknown, columns: unknown): RecordValue[] {
  if (!Array.isArray(rows)) return []
  const names = Array.isArray(columns) ? columns.filter(Boolean).map((col) => String(col)) : []
  return rows
    .map((row) => {
      if (row && typeof row === 'object' && !Array.isArray(row)) return { ...row }
      if (!Array.isArray(row) || names.length === 0) return null
      const mapped: RecordValue = {}
      names.forEach((column, idx) => {
        mapped[column] = row[idx]
      })
      return mapped
    })
    .filter((row): row is RecordValue => Boolean(row))
}

function parseArtifactTimestampMs(value: unknown): number {
  const raw = String(value || '').trim()
  if (!raw) return 0
  const parsed = Date.parse(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

function sortArtifactsNewestFirst(artifacts: unknown): RecordValue[] {
  if (!Array.isArray(artifacts)) return []
  return artifacts
    .filter((artifact): artifact is RecordValue => (
      Boolean(artifact && typeof artifact === 'object' && !Array.isArray(artifact))
    ))
    .sort((left, right) => {
    const delta = parseArtifactTimestampMs(right.created_at) - parseArtifactTimestampMs(left.created_at)
    if (delta !== 0) return delta
    return String(right.artifact_id || '').localeCompare(String(left.artifact_id || ''))
  })
}

function buildArtifactDataframes(artifacts: unknown): NamedData[] {
  return sortArtifactsNewestFirst(artifacts)
    .filter((item) => String(item.kind || '').toLowerCase() === 'dataframe')
    .map((item, index) => {
      const schema = Array.isArray(item.schema) ? item.schema : []
      const columns = schema
        .map((column) => String(asRecord(column).name || ''))
        .filter(Boolean)
      const previewRows = normalizePreviewRows(item.preview_rows, columns)
      const logicalName = String(item.logical_name || '').trim()
      const displayName = String(item.display_name || '').trim()
      const name = displayName || logicalName || `dataframe_${index + 1}`
      return {
        name,
        data: {
          artifact_id: item.artifact_id || null,
          logical_name: logicalName || undefined,
          display_name: displayName || undefined,
          row_count: Number.isFinite(Number(item.row_count)) ? Number(item.row_count) : previewRows.length,
          columns,
          data: previewRows,
        },
      }
    })
}

function buildArtifactFigures(artifacts: unknown): FigureData[] {
  return sortArtifactsNewestFirst(artifacts)
    .filter((item) => String(item.kind || '').toLowerCase() === 'figure')
    .flatMap((item, index): FigureData[] => {
      const payloadRecord = asRecord(item.payload)
      const payload = payloadRecord.figure ?? item.payload
      const normalizedFigure = normalizePlotlyFigure(payload)
      if (!normalizedFigure) return []
      const logicalName = String(item.logical_name || '').trim()
      const displayName = String(item.display_name || '').trim()
      const artifactId = String(item.artifact_id || normalizedFigure.artifact_id || '').trim()
      return [{
        name: displayName || logicalName || `figure_${index + 1}`,
        artifact_id: artifactId || undefined,
        logical_name: logicalName || undefined,
        display_name: displayName || undefined,
        data: normalizedFigure,
      }]
    })
}

function buildArtifactScalars(artifacts: unknown): ScalarData[] {
  return sortArtifactsNewestFirst(artifacts)
    .filter((item) => String(item.kind || '').toLowerCase() === 'scalar')
    .map((item, index) => {
      const logicalName = String(item.logical_name || '').trim()
      const displayName = String(item.display_name || '').trim()
      const payload = item.payload
      const value = payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'value')
        ? asRecord(payload).value
        : payload
      return {
        name: displayName || logicalName || `scalar_${index + 1}`,
        value,
      }
    })
}

export function buildExecutionViewModel(
  responseValue: unknown,
  options: ExecutionViewModelOptions = {},
): ExecutionViewModel {
  const response = asRecord(responseValue)
  const variables = asRecord(response.variables)
  const opts = {
    dataframeLine: options.dataframeLine
      ?? ((count: number) => `✅ ${count} dataframe(s) found. Available in Results.`),
    figureLine: options.figureLine
      ?? ((count: number) => `✅ ${count} figure(s) found. Available in Results.`),
    scalarLine: options.scalarLine
      ?? ((count: number) => `✅ ${count} scalar(s) captured.`),
    dataframeParseErrorLine: options.dataframeParseErrorLine ?? '⚠️ Failed to parse dataframe data.',
    figureParseErrorLine: options.figureParseErrorLine ?? '⚠️ Failed to parse figure data.',
    scalarParseErrorLine: options.scalarParseErrorLine ?? '⚠️ Failed to parse scalar data.',
    successLine: options.successLine ?? '✅ Cell executed successfully!',
    includeVariableSummary: options.includeVariableSummary ?? false,
    variableSummaryLine: options.variableSummaryLine ?? ((counts: ExecutionCounts) =>
      `Variables created: ${counts.dataframes} dataframe(s), ${counts.figures} figure(s), ${counts.scalars} scalar(s)`),
  }

  const outputParts: string[] = []

  if (typeof response.execution_time === 'number' && Number.isFinite(response.execution_time)) {
    outputParts.push(`Execution time: ${response.execution_time.toFixed(3)}s`)
  }

  if (response.output) {
    outputParts.push(`Output:\n${response.output}`)
  }

  if (response.error) {
    outputParts.push(`Error: ${response.error}`)
  }

  const parsedDataframes = parseObjectBucket(variables.dataframes, { parseJson: true })
  const parsedFigures = parseObjectBucket(variables.figures, { parseJson: true })
  const parsedScalars = parseObjectBucket(variables.scalars)

  const parsedDataframeEntries = parsedDataframes.entries.map(({ name, value }) => ({ name, data: value }))
  const parsedFigureEntries = parsedFigures.entries
    .flatMap(({ name, value }): FigureData[] => {
      const normalizedFigure = normalizePlotlyFigure(value)
      if (!normalizedFigure) return []
      const valueRecord = asRecord(value)
      const artifactId = String(valueRecord.artifact_id || normalizedFigure.artifact_id || '').trim()
      const logicalName = String(valueRecord.logical_name || valueRecord.name || '').trim()
      return [{
        name,
        artifact_id: artifactId || undefined,
        logical_name: logicalName || undefined,
        data: normalizedFigure,
      }]
    })
  const parsedScalarEntries = parsedScalars.entries.map(({ name, value }) => ({ name, value }))

  const artifactDataframes = buildArtifactDataframes(response.artifacts)
  const artifactFigures = buildArtifactFigures(response.artifacts)
  const artifactScalars = buildArtifactScalars(response.artifacts)

  const mergedDataframes = mergeDataframeEntries(artifactDataframes, parsedDataframeEntries)
  const mergedFigures = dedupeByName([...artifactFigures, ...parsedFigureEntries])
  const mergedScalars = dedupeByName([...artifactScalars, ...parsedScalarEntries])

  if (mergedDataframes.length > 0) {
    outputParts.push(opts.dataframeLine(mergedDataframes.length))
  }
  if (parsedDataframes.failed > 0) {
    outputParts.push(opts.dataframeParseErrorLine)
  }

  if (mergedFigures.length > 0) {
    outputParts.push(opts.figureLine(mergedFigures.length))
  }
  if (parsedFigures.failed > 0) {
    outputParts.push(opts.figureParseErrorLine)
  }

  if (mergedScalars.length > 0) {
    outputParts.push(opts.scalarLine(mergedScalars.length))
  }
  if (parsedScalars.failed > 0) {
    outputParts.push(opts.scalarParseErrorLine)
  }

  if (opts.includeVariableSummary) {
    outputParts.push(
      opts.variableSummaryLine({
        dataframes: mergedDataframes.length,
        figures: mergedFigures.length,
        scalars: mergedScalars.length,
      }),
    )
  }

  if (!response.error && opts.successLine) {
    outputParts.push(opts.successLine)
  }

  return {
    output: outputParts.join('\n\n'),
    dataframes: mergedDataframes,
    figures: mergedFigures,
    scalars: mergedScalars,
    counts: {
      dataframes: mergedDataframes.length,
      figures: mergedFigures.length,
      scalars: mergedScalars.length,
    },
  }
}
