import { nativeApp } from '../api/native'

function normalizeExternalUrl(rawUrl: unknown): string {
  const input = String(rawUrl || '').trim()
  if (!input) return ''

  if (/^[a-zA-Z][a-zA-Z\d+.-]*:/.test(input)) {
    return input
  }

  if (typeof window === 'undefined') {
    return input
  }

  if (input.startsWith('//')) {
    return `${window.location.protocol}${input}`
  }

  if (input.startsWith('/')) {
    return `${window.location.origin}${input}`
  }

  return `${window.location.origin}/${input.replace(/^\/+/, '')}`
}

export async function openExternalUrl(rawUrl: unknown): Promise<boolean> {
  const url = normalizeExternalUrl(rawUrl)
  if (!url) return false

  const app = nativeApp()
  if (app?.OpenExternalURL) {
    try {
      await app.OpenExternalURL(url)
      return true
    } catch (error) {
      console.error('❌ Failed to open external URL via Go desktop command:', error)
      return false
    }
  }

  if (typeof window !== 'undefined') {
    const openedWindow = window.open(url, '_blank', 'noopener,noreferrer')
    if (openedWindow) {
      return true
    }
    window.location.assign(url)
    return true
  }

  return false
}

export default {
  openExternalUrl,
}
