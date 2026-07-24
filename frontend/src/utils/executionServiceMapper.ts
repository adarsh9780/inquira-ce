type RecordValue = Record<string, unknown>

export interface ExecutionVariableBuckets {
  dataframes: Record<string, RecordValue>
  figures: Record<string, RecordValue>
  scalars: Record<string, unknown>
}

function asRecord(value: unknown): RecordValue {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as RecordValue
    : {}
}

function asRecordBucket(value: unknown): Record<string, RecordValue> {
  return Object.fromEntries(
    Object.entries(asRecord(value))
      .filter((entry): entry is [string, RecordValue] => (
        Boolean(entry[1] && typeof entry[1] === 'object' && !Array.isArray(entry[1]))
      )),
  )
}

function normalizeVariables(value: unknown): ExecutionVariableBuckets {
  const variables = asRecord(value)
  return {
    dataframes: asRecordBucket(variables.dataframes),
    figures: asRecordBucket(variables.figures),
    scalars: asRecord(variables.scalars),
  }
}

export function mapExecutionServiceResponse(responseValue: unknown) {
  const response = asRecord(responseValue)
  return {
    success: response.success !== false,
    stdout: response.stdout || '',
    stderr: response.stderr || '',
    hasStdout: Boolean(response.has_stdout ?? response.hasStdout ?? response.stdout),
    hasStderr: Boolean(response.has_stderr ?? response.hasStderr ?? response.stderr),
    error: response.error || null,
    result: response.result || null,
    resultType: response.result_type || null,
    resultKind: response.result_kind || null,
    resultName: response.result_name || null,
    runId: response.run_id || null,
    artifacts: Array.isArray(response.artifacts)
      ? response.artifacts.filter((item): item is RecordValue => (
        Boolean(item && typeof item === 'object' && !Array.isArray(item))
      ))
      : [],
    variables: normalizeVariables(response.variables),
  }
}
