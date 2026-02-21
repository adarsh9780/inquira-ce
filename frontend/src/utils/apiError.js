export function extractApiErrorMessage(error, fallbackMessage = 'Failed to generate code. Please try again.') {
  const detail = error?.response?.data?.detail

  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (typeof first === 'string' && first.trim()) {
      return first.trim()
    }
    if (first && typeof first === 'object' && typeof first.msg === 'string' && first.msg.trim()) {
      return first.msg.trim()
    }
  }

  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message.trim()
  }

  return fallbackMessage
}
