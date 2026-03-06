function isDataFrameLike(value) {
  return Boolean(value && typeof value === 'object' && value.columns && value.data)
}

function isFigureLike(value) {
  return Boolean(value && typeof value === 'object' && value.data && value.layout)
}

function classifyResult(result, resultType) {
  if (resultType === 'DataFrame' || isDataFrameLike(result)) return 'dataframe'
  if (resultType === 'Figure' || isFigureLike(result)) return 'figure'
  return 'scalar'
}

function isObject(value) {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function normalizeBucket(value) {
  return isObject(value) ? value : {}
}

function normalizeDataFrameValue(value) {
  if (!value) return value
  if (Array.isArray(value)) return value
  if (!isDataFrameLike(value)) return value
  if (!Array.isArray(value.columns) || !Array.isArray(value.data)) return value

  // Convert pandas "split" JSON (columns + row arrays) into row objects.
  const mappedRows = value.data.map((row) => {
    if (!Array.isArray(row)) return row
    const result = {}
    value.columns.forEach((col, idx) => {
      result[col] = row[idx]
    })
    return result
  })

  // Preserve backend artifact metadata for paginated fetches.
  if (Object.prototype.hasOwnProperty.call(value, 'artifact_id') || Object.prototype.hasOwnProperty.call(value, 'row_count')) {
    return { ...value, data: mappedRows }
  }

  return mappedRows
}

function normalizeDataFrameBucket(bucket) {
  const normalized = normalizeBucket(bucket)
  const entries = Object.entries(normalized).map(([key, value]) => [
    key,
    normalizeDataFrameValue(value),
  ])
  return Object.fromEntries(entries)
}

function isVariableBundle(value) {
  if (!isObject(value)) return false
  return ['dataframes', 'figures', 'scalars'].some((key) => isObject(value[key]))
}

function normalizeArtifactPreviewRows(rows, schemaColumns = []) {
  if (!Array.isArray(rows)) return []
  const columnNames = Array.isArray(schemaColumns)
    ? schemaColumns.map((col) => (isObject(col) ? String(col?.name || '') : String(col || ''))).filter(Boolean)
    : []
  return rows
    .map((row) => {
      if (isObject(row)) return { ...row }
      if (!Array.isArray(row)) return null
      if (columnNames.length === 0) return null
      const mapped = {}
      columnNames.forEach((col, idx) => {
        mapped[col] = row[idx]
      })
      return mapped
    })
    .filter(Boolean)
}

function normalizeArtifactList(rawArtifacts) {
  if (!Array.isArray(rawArtifacts)) return []
  return rawArtifacts
    .map((item) => {
      if (!isObject(item)) return null
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
            .filter(Boolean)
        : []
      return {
        ...item,
        kind,
        artifact_id: item.artifact_id ? String(item.artifact_id) : null,
        logical_name: item.logical_name ? String(item.logical_name) : '',
        row_count: Number.isFinite(Number(item.row_count)) ? Number(item.row_count) : 0,
        schema,
        preview_rows: normalizeArtifactPreviewRows(item.preview_rows, schema),
      }
    })
    .filter(Boolean)
}

export function normalizeExecutionResponse(raw) {
  const stdout = String(raw?.stdout || '')
  const stderr = String(raw?.stderr || '')
  const hasStdout = Boolean(raw?.has_stdout ?? raw?.hasStdout ?? stdout)
  const hasStderr = Boolean(raw?.has_stderr ?? raw?.hasStderr ?? stderr)
  const error = raw?.error || null
  const result = raw?.result ?? null
  const resultType = raw?.result_type ?? raw?.resultType ?? null
  const resultKind = raw?.result_kind ?? raw?.resultKind ?? null
  const resultName = raw?.result_name ?? raw?.resultName ?? null
  const runId = raw?.run_id ?? raw?.runId ?? null
  const artifacts = normalizeArtifactList(raw?.artifacts)

  const response = {
    success: raw?.success !== false,
    stdout,
    stderr,
    has_stdout: hasStdout,
    has_stderr: hasStderr,
    error,
    result,
    result_type: resultType,
    result_kind: resultKind,
    result_name: resultName,
    run_id: runId ? String(runId) : null,
    artifacts,
    output: [stdout, stderr].filter(Boolean).join('\n'),
    variables: {
      dataframes: normalizeDataFrameBucket(raw?.variables?.dataframes),
      figures: normalizeBucket(raw?.variables?.figures),
      scalars: normalizeBucket(raw?.variables?.scalars),
    },
  }

  if (result !== null && result !== undefined && isVariableBundle(result)) {
    Object.assign(response.variables.dataframes, normalizeDataFrameBucket(result.dataframes))
    Object.assign(response.variables.figures, normalizeBucket(result.figures))
    Object.assign(response.variables.scalars, normalizeBucket(result.scalars))
  } else if (result !== null && result !== undefined) {
    const bucket = classifyResult(result, resultType)
    if (bucket === 'dataframe') {
      response.variables.dataframes.result = normalizeDataFrameValue(result)
    } else if (bucket === 'figure') {
      response.variables.figures.result = result
    } else {
      response.variables.scalars.result = result
    }
  }

  return response
}
