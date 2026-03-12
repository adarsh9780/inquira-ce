export async function persistExportFile({
  defaultFileName,
  mimeType,
  payload,
  tauriFilters,
  browserFileTypes
}) {
  if (window.__TAURI_INTERNALS__) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const savePath = await save({
      defaultPath: defaultFileName,
      filters: Array.isArray(tauriFilters) ? tauriFilters : []
    })
    if (!savePath) return false
    const { writeFile } = await import('@tauri-apps/plugin-fs')
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
