export function workspaceInitials(name, fallback = 'WS') {
  const fallbackText = String(fallback || 'WS').trim().replace(/[^a-zA-Z0-9]/g, '')
  const safeFallback = (fallbackText || 'WS').slice(0, 2).toUpperCase()
  const raw = String(name || '').trim()
  if (!raw) return safeFallback

  const parts = raw
    .split(/[\s._/-]+/)
    .map((part) => part.trim().replace(/[^a-zA-Z0-9]/g, ''))
    .filter(Boolean)

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }

  return (parts[0] || raw).slice(0, 2).toUpperCase()
}
