export function mapExecutionServiceResponse(response) {
  return {
    success: response?.success !== false,
    stdout: response?.stdout || '',
    stderr: response?.stderr || '',
    hasStdout: Boolean(response?.has_stdout ?? response?.hasStdout ?? response?.stdout),
    hasStderr: Boolean(response?.has_stderr ?? response?.hasStderr ?? response?.stderr),
    error: response?.error || null,
    result: response?.result || null,
    resultType: response?.result_type || null,
    resultKind: response?.result_kind || null,
    resultName: response?.result_name || null,
    variables: response?.variables || { dataframes: {}, figures: {}, scalars: {} },
  }
}
