import { invoke } from '@tauri-apps/api/core'

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function normalizeExternalUrl(rawUrl) {
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

export async function openExternalUrl(rawUrl) {
  const url = normalizeExternalUrl(rawUrl)
  if (!url) return false

  const app = wailsApp()
  if (app?.OpenExternalURL) {
    try {
      await app.OpenExternalURL(url)
      return true
    } catch (error) {
      console.error('❌ Failed to open external URL via Go desktop command:', error)
      return false
    }
  }

  const isTauriDesktop = typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__

  if (isTauriDesktop) {
    try {
      await invoke('open_external_url', { url })
      return true
    } catch (error) {
      console.error('❌ Failed to open external URL via desktop command:', error)
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
