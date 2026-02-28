export function mapExecutionServiceResponse(response) {
  return {
    success: response?.success !== false,
    stdout: response?.stdout || '',
    stderr: response?.stderr || '',
    error: response?.error || null,
    result: response?.result || null,
    resultType: response?.result_type || null,
    variables: response?.variables || { dataframes: {}, figures: {}, scalars: {} },
  }
}
