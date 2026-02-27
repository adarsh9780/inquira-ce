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

export function normalizeExecutionResponse(raw) {
  const stdout = String(raw?.stdout || '')
  const stderr = String(raw?.stderr || '')
  const error = raw?.error || null
  const result = raw?.result ?? null
  const resultType = raw?.result_type || null

  const response = {
    success: raw?.success !== false,
    stdout,
    stderr,
    error,
    result,
    result_type: resultType,
    output: [stdout, stderr].filter(Boolean).join('\n'),
    variables: {
      dataframes: {},
      figures: {},
      scalars: {},
    },
  }

  if (result !== null && result !== undefined) {
    const bucket = classifyResult(result, resultType)
    if (bucket === 'dataframe') {
      response.variables.dataframes.result = result
    } else if (bucket === 'figure') {
      response.variables.figures.result = result
    } else {
      response.variables.scalars.result = result
    }
  }

  return response
}

