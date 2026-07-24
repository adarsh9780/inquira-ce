type ErrorRecord = Record<string, unknown>

function asRecord(value: unknown): ErrorRecord | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as ErrorRecord
    : null
}

function parseJsonLike(value: unknown): unknown {
  const text = String(value || '').trim()
  if (!text) return null
  if (!(text.startsWith('{') || text.startsWith('['))) return null
  try {
    return JSON.parse(text)
  } catch (_error) {
    return null
  }
}

export function extractApiErrorMessageFromPayload(
  payload: unknown,
  fallbackMessage = '',
): string {
  if (typeof payload === 'string' && payload.trim()) {
    const parsed = parseJsonLike(payload)
    if (parsed) {
      return extractApiErrorMessageFromPayload(parsed, fallbackMessage)
    }
    return payload.trim()
  }

  if (Array.isArray(payload) && payload.length > 0) {
    const first = payload[0]
    const nested = extractApiErrorMessageFromPayload(first, '')
    return nested || fallbackMessage
  }

  const record = asRecord(payload)
  if (record) {
    const directFields = [
      record.detail,
      record.message,
      record.msg,
      record.error,
    ]
    for (const candidate of directFields) {
      const nested = extractApiErrorMessageFromPayload(candidate, '')
      if (nested) return nested
    }
  }

  return fallbackMessage
}

export function extractApiErrorMessage(
  error: unknown,
  fallbackMessage = 'Failed to generate code. Please try again.',
): string {
  const errorRecord = asRecord(error)
  const response = asRecord(errorRecord?.response)
  const responseData = response?.data
  const detail = extractApiErrorMessageFromPayload(
    responseData
      ?? errorRecord?.data
      ?? asRecord(responseData)?.detail
      ?? errorRecord?.message,
    '',
  )

  if (detail) return detail
  return fallbackMessage
}
