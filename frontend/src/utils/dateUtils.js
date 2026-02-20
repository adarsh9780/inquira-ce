/**
 * Formats a timestamp into a human-readable relative time string
 * @param {number|string} timestamp - The timestamp to format
 * @returns {string} Formatted time string
 */
export function formatTimestamp(timestamp) {
  const date = new Date(timestamp)
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