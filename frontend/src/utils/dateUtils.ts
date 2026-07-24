export type TimestampInput = Date | number | string | null | undefined

export function formatTimestamp(timestamp: TimestampInput): string {
  const date = parseTimestamp(timestamp)
  if (!date) return ''

  const now = new Date()
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))

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

export function formatCompactRelativeTimestamp(
  timestamp: TimestampInput,
  now: TimestampInput = new Date(),
): string {
  const date = parseTimestamp(timestamp)
  const current = parseTimestamp(now)
  if (!date || !current) return ''

  const diffMs = Math.max(0, current.getTime() - date.getTime())
  const minutes = Math.max(1, Math.floor(diffMs / (1000 * 60)))

  if (minutes < 60) return `${minutes}m`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`

  const days = Math.floor(hours / 24)
  if (days < 14) return `${days}d`

  const weeks = Math.floor(days / 7)
  if (days < 30) return `${weeks}w`

  const months = Math.floor(days / 30)
  if (days < 365) return `${Math.max(1, months)}mo`

  const years = Math.floor(days / 365)
  return `${Math.max(1, years)}y`
}

export function formatExactTimestamp(timestamp: TimestampInput): string {
  const date = parseTimestamp(timestamp)
  if (!date) return 'No date available'

  const day = date.getUTCDate()
  const month = date.toLocaleString('en-GB', {
    month: 'short',
    timeZone: 'UTC',
  })
  const year = date.getUTCFullYear()
  const time = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'UTC',
  })

  return `${day} ${month} ${year}, ${time}`
}

export function parseTimestamp(timestamp: TimestampInput): Date | null {
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
