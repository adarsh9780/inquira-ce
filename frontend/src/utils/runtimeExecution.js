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

export function normalizeExecutionResponse(raw) {
  const stdout = String(raw?.stdout || '')
  const stderr = String(raw?.stderr || '')
  const error = raw?.error || null
  const result = raw?.result ?? null
  const resultType = raw?.result_type ?? raw?.resultType ?? null

  const response = {
    success: raw?.success !== false,
    stdout,
    stderr,
    error,
    result,
    result_type: resultType,
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
