function parseJsonLike(value) {
  const text = String(value || '').trim()
  if (!text) return null
  if (!(text.startsWith('{') || text.startsWith('['))) return null
  try {
    return JSON.parse(text)
  } catch (_error) {
    return null
  }
}

export function extractApiErrorMessageFromPayload(payload, fallbackMessage = '') {
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

  if (payload && typeof payload === 'object') {
    const directFields = [
      payload.detail,
      payload.message,
      payload.msg,
      payload.error,
    ]
    for (const candidate of directFields) {
      const nested = extractApiErrorMessageFromPayload(candidate, '')
      if (nested) return nested
    }
  }

  return fallbackMessage
}

export function extractApiErrorMessage(error, fallbackMessage = 'Failed to generate code. Please try again.') {
  const detail = extractApiErrorMessageFromPayload(
    error?.response?.data
      ?? error?.data
      ?? error?.response?.data?.detail
      ?? error?.message,
    '',
  )

  if (detail) return detail
  return fallbackMessage
}
