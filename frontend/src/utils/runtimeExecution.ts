type RecordValue = Record<string, unknown>
type ValueBucket = Record<string, unknown>

export interface NormalizedExecutionResponse {
  success: boolean
  stdout: string
  stderr: string
  has_stdout: boolean
  has_stderr: boolean
  stdout_truncated: boolean
  stderr_truncated: boolean
  output_truncated: boolean
  error: unknown
  result: unknown
  result_type: unknown
  result_kind: unknown
  result_name: unknown
  run_id: string | null
  artifacts: RecordValue[]
  output: string
  variables: {
    dataframes: ValueBucket
    figures: ValueBucket
    scalars: ValueBucket
  }
}

function isObject(value: unknown): value is RecordValue {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function isDataFrameLike(value: unknown): value is RecordValue {
  return isObject(value) && Boolean(value.columns && (value.data || value.rows))
}

function isFigureLike(value: unknown): value is RecordValue {
  return isObject(value) && Boolean(value.data && value.layout)
}

function classifyResult(result: unknown, resultType: unknown) {
  if (resultType === 'DataFrame' || isDataFrameLike(result)) return 'dataframe'
  if (resultType === 'Figure' || isFigureLike(result)) return 'figure'
  return 'scalar'
}

function normalizeBucket(value: unknown): ValueBucket {
  return isObject(value) ? value : {}
}

function normalizeDataFrameValue(value: unknown): unknown {
  if (!value) return value
  if (Array.isArray(value)) return value
  if (!isDataFrameLike(value)) return value
  const rawRows = Array.isArray(value.data) ? value.data : value.rows
  const columns = value.columns
  if (!Array.isArray(columns) || !Array.isArray(rawRows)) return value

  // Convert pandas "split" JSON (columns + row arrays) into row objects.
  const mappedRows = rawRows.map((row): unknown => {
    if (!Array.isArray(row)) return row
    const result: RecordValue = {}
    columns.forEach((col, idx) => {
      result[String(col)] = row[idx]
    })
    return result
  })

  // Preserve backend artifact metadata for paginated fetches.
  if (Object.prototype.hasOwnProperty.call(value, 'artifact_id') || Object.prototype.hasOwnProperty.call(value, 'row_count')) {
    return { ...value, data: mappedRows }
  }

  return mappedRows
}

function normalizeDataFrameBucket(bucket: unknown): ValueBucket {
  const normalized = normalizeBucket(bucket)
  const entries = Object.entries(normalized).map(([key, value]) => [
    key,
    normalizeDataFrameValue(value),
  ])
  return Object.fromEntries(entries)
}

function isVariableBundle(value: unknown): value is RecordValue {
  if (!isObject(value)) return false
  return ['dataframes', 'figures', 'scalars'].some((key) => isObject(value[key]))
}

function normalizeArtifactPreviewRows(
  rows: unknown,
  schemaColumns: unknown = [],
): RecordValue[] {
  if (!Array.isArray(rows)) return []
  const columnNames = Array.isArray(schemaColumns)
    ? schemaColumns.map((col) => (isObject(col) ? String(col.name || '') : String(col || ''))).filter(Boolean)
    : []
  return rows
    .map((row) => {
      if (isObject(row)) return { ...row }
      if (!Array.isArray(row)) return null
      if (columnNames.length === 0) return null
      const mapped: RecordValue = {}
      columnNames.forEach((col, idx) => {
        mapped[col] = row[idx]
      })
      return mapped
    })
    .filter((row): row is RecordValue => Boolean(row))
}

function normalizeArtifactList(rawArtifacts: unknown): RecordValue[] {
  if (!Array.isArray(rawArtifacts)) return []
  return rawArtifacts
    .flatMap((item): RecordValue[] => {
      if (!isObject(item)) return []
      const kind = String(item.kind || '').trim().toLowerCase()
      const schema = Array.isArray(item.schema)
        ? item.schema
            .map((col) => {
              if (isObject(col)) {
                return {
                  name: String(col.name || ''),
                  dtype: String(col.dtype || ''),
                }
              }
              return null
            })
            .filter((column): column is { name: string; dtype: string } => Boolean(column))
        : []
      return [{
        ...item,
        kind,
        artifact_id: item.artifact_id ? String(item.artifact_id) : null,
        logical_name: item.logical_name ? String(item.logical_name) : '',
        display_name: item.display_name ? String(item.display_name) : '',
        row_count: Number.isFinite(Number(item.row_count)) ? Number(item.row_count) : 0,
        schema,
        preview_rows: normalizeArtifactPreviewRows(item.preview_rows, schema),
      }]
    })
}

export function normalizeExecutionResponse(rawValue: unknown): NormalizedExecutionResponse {
  const raw = isObject(rawValue) ? rawValue : {}
  const variables = isObject(raw.variables) ? raw.variables : {}
  const stdout = String(raw.stdout || '')
  const stderr = String(raw.stderr || '')
  const hasStdout = Boolean(raw.has_stdout ?? raw.hasStdout ?? stdout)
  const hasStderr = Boolean(raw.has_stderr ?? raw.hasStderr ?? stderr)
  const error = raw.error || null
  const result = raw.result ?? null
  const resultType = raw.result_type ?? raw.resultType ?? null
  const resultKind = raw.result_kind ?? raw.resultKind ?? null
  const resultName = raw.result_name ?? raw.resultName ?? null
  const runId = raw.run_id ?? raw.runId ?? null
  const artifacts = normalizeArtifactList(raw.artifacts)

  const response: NormalizedExecutionResponse = {
    success: raw.success !== false,
    stdout,
    stderr,
    has_stdout: hasStdout,
    has_stderr: hasStderr,
    stdout_truncated: Boolean(raw.stdout_truncated),
    stderr_truncated: Boolean(raw.stderr_truncated),
    output_truncated: Boolean(raw.output_truncated || raw.stdout_truncated || raw.stderr_truncated),
    error,
    result,
    result_type: resultType,
    result_kind: resultKind,
    result_name: resultName,
    run_id: runId ? String(runId) : null,
    artifacts,
    output: [stdout, stderr].filter(Boolean).join('\n'),
    variables: {
      dataframes: normalizeDataFrameBucket(variables.dataframes),
      figures: normalizeBucket(variables.figures),
      scalars: normalizeBucket(variables.scalars),
    },
  }

  if (result !== null && result !== undefined && isVariableBundle(result)) {
    Object.assign(response.variables.dataframes, normalizeDataFrameBucket(result.dataframes))
    Object.assign(response.variables.figures, normalizeBucket(result.figures))
    Object.assign(response.variables.scalars, normalizeBucket(result.scalars))
  } else if (result !== null && result !== undefined) {
    const bucket = classifyResult(result, resultType)
    if (bucket === 'dataframe') {
      response.variables.dataframes[String(resultName || 'result')] = normalizeDataFrameValue(result)
    } else if (bucket === 'figure') {
      response.variables.figures[String(resultName || 'result')] = result
    } else {
      response.variables.scalars[String(resultName || 'result')] = result
    }
  }

  return response
}

export function latestExpressionVariables(normalizedValue: unknown) {
  const normalized = isObject(normalizedValue) ? normalizedValue : {}
  const source = isObject(normalized.variables) ? normalized.variables : {}
  const preferredName = String(normalized.result_name || 'result').trim() || 'result'
  const resultOnly = (bucket: unknown): ValueBucket => {
    if (!isObject(bucket)) return {}
    if (Object.prototype.hasOwnProperty.call(bucket, preferredName)) {
      return { [preferredName]: bucket[preferredName] }
    }
    if (!Object.prototype.hasOwnProperty.call(bucket, 'result')) return {}
    return { result: bucket.result }
  }

  return {
    dataframes: resultOnly(source.dataframes),
    figures: resultOnly(source.figures),
    scalars: resultOnly(source.scalars),
  }
}
