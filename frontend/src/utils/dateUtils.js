/**
 * Formats a timestamp into a human-readable relative time string
 * @param {number|string} timestamp - The timestamp to format
 * @returns {string} Formatted time string
 */
export function formatTimestamp(timestamp) {
  const date = parseTimestamp(timestamp)
  if (!date) return ''

  const now = new Date()
  const diffInMinutes = Math.floor((now - date) / (1000 * 60))

  if (diffInMinutes < 1) {
    return 'Just now'
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`
  } else if (diffInMinutes < 1440) {
    const hours = Math.floor(diffInMinutes / 60)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  } else {
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

export function parseTimestamp(timestamp) {
  if (timestamp instanceof Date) {
    return Number.isNaN(timestamp.getTime()) ? null : timestamp
  }
  if (typeof timestamp === 'number') {
    const date = new Date(timestamp)
    return Number.isNaN(date.getTime()) ? null : date
  }

  const raw = String(timestamp || '').trim()
  if (!raw) return null

  const isoLikeDateTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(raw)
  const hasExplicitTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)
  const value = isoLikeDateTime && !hasExplicitTimezone ? `${raw}Z` : raw
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}
