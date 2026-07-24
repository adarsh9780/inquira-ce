export function filenameFromPath(pathValue: unknown, fallback = ''): string {
  const value = String(pathValue || '').trim()
  if (!value) return fallback
  const normalized = value.replace(/\\/g, '/')
  const parts = normalized.split('/').filter(Boolean)
  return parts.at(-1) || fallback
}
