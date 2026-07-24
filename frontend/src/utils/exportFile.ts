import { bytesToBase64 } from './exportEncoding'
import { nativeApp } from '../api/native'

export interface ExportFilter {
  name: string
  extensions: string[]
}

export interface BrowserFileType {
  description?: string
  accept: Record<string, string[]>
}

export interface PersistExportFileOptions {
  defaultFileName: string
  mimeType: string
  payload: string | Uint8Array
  nativeFilters?: ExportFilter[]
  browserFileTypes?: BrowserFileType[]
}

interface BrowserWritableFile {
  write(data: string | Uint8Array): Promise<void>
  close(): Promise<void>
}

interface BrowserFileHandle {
  createWritable(): Promise<BrowserWritableFile>
}

type WindowWithSavePicker = Window & {
  showSaveFilePicker?: (options: {
    suggestedName: string
    types: BrowserFileType[]
  }) => Promise<BrowserFileHandle>
}

export async function persistExportFile({
  defaultFileName,
  mimeType,
  payload,
  nativeFilters = [],
  browserFileTypes = [],
}: PersistExportFileOptions): Promise<boolean> {
  const app = nativeApp()
  if (app?.SaveExportFile) {
    try {
      return Boolean(await app.SaveExportFile({
        default_file_name: defaultFileName,
        content_base64: bytesToBase64(payload),
        filters: nativeFilters.map((filter) => ({
          name: String(filter.name || ''),
          extensions: Array.isArray(filter.extensions) ? filter.extensions.map(String) : [],
        })),
      }))
    } catch (error) {
      console.error('Failed to save export through Wails:', error)
      throw error
    }
  }

  const browserWindow = window as WindowWithSavePicker
  if (typeof browserWindow.showSaveFilePicker === 'function') {
    try {
      const handle = await browserWindow.showSaveFilePicker({
        suggestedName: defaultFileName,
        types: browserFileTypes,
      })
      const writable = await handle.createWritable()
      await writable.write(payload)
      await writable.close()
      return true
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === 'AbortError') return false
      throw error
    }
  }

  const blobData = payload instanceof Uint8Array
    ? Uint8Array.from(payload)
    : new TextEncoder().encode(String(payload || ''))
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
