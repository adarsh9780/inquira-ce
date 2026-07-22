import { writeFile } from '@tauri-apps/plugin-fs'
import { bytesToBase64 } from './exportEncoding'

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

export async function persistExportFile({
  defaultFileName,
  mimeType,
  payload,
  tauriFilters,
  browserFileTypes
}) {
  const app = wailsApp()
  if (app?.SaveExportFile) {
    try {
      return Boolean(await app.SaveExportFile({
        default_file_name: defaultFileName,
        content_base64: bytesToBase64(payload),
        filters: (Array.isArray(tauriFilters) ? tauriFilters : []).map((filter) => ({
          name: String(filter?.name || ''),
          extensions: Array.isArray(filter?.extensions) ? filter.extensions.map(String) : [],
        })),
      }))
    } catch (error) {
      console.error('Failed to save export through Wails:', error)
      throw error
    }
  }

  if (window.__TAURI_INTERNALS__) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const savePath = await save({
      defaultPath: defaultFileName,
      filters: Array.isArray(tauriFilters) ? tauriFilters : []
    })
    if (!savePath) return false
    await writeFile(savePath, payload)
    return true
  }

  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: defaultFileName,
        types: Array.isArray(browserFileTypes) ? browserFileTypes : []
      })
      const writable = await handle.createWritable()
      await writable.write(payload)
      await writable.close()
      return true
    } catch (error) {
      if (error?.name === 'AbortError') return false
      throw error
    }
  }

  const blobData = payload instanceof Uint8Array ? payload : new TextEncoder().encode(String(payload || ''))
  const blob = new Blob([blobData], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', defaultFileName)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return true
}
