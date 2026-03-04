import {
  BaseDirectory,
  create,
  exists,
  mkdir,
  readTextFile
} from '@tauri-apps/plugin-fs'

const SNAPSHOT_DIR = 'state'
const DEFAULT_SCOPE = 'anonymous'

function isTauriRuntime() {
  return typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
}

async function ensureDirectory() {
  await mkdir(SNAPSHOT_DIR, { baseDir: BaseDirectory.AppData, recursive: true })
}

function normalizeScope(scope) {
  const raw = String(scope || '').trim().toLowerCase()
  if (!raw) return DEFAULT_SCOPE
  const cleaned = raw.replace(/[^a-z0-9_-]/g, '_')
  return cleaned || DEFAULT_SCOPE
}

function snapshotPath(scope) {
  const key = normalizeScope(scope)
  return `${SNAPSHOT_DIR}/session_state_${key}.json`
}

function tmpSnapshotPath(scope) {
  return `${snapshotPath(scope)}.tmp`
}

async function atomicWriteJson(path, payload) {
  const serialized = JSON.stringify(payload, null, 2)
  const file = await create(path, { baseDir: BaseDirectory.AppData })
  try {
    await file.write(new TextEncoder().encode(serialized))
    // Older @tauri-apps/plugin-fs builds may not expose sync().
    if (typeof file.sync === 'function') {
      await file.sync()
    }
  } finally {
    await file.close()
  }
}

export const localStateService = {
  async loadSnapshot(scope = DEFAULT_SCOPE) {
    if (!isTauriRuntime()) return null
    try {
      const resolvedPath = snapshotPath(scope)
      const fileExists = await exists(resolvedPath, { baseDir: BaseDirectory.AppData })
      if (!fileExists) return null
      const raw = await readTextFile(resolvedPath, { baseDir: BaseDirectory.AppData })
      if (!raw || !raw.trim()) return null
      return JSON.parse(raw)
    } catch (error) {
      console.warn('Failed to load local state snapshot:', error)
      return null
    }
  },

  async saveSnapshot(snapshot, scope = DEFAULT_SCOPE) {
    if (!isTauriRuntime()) return false
    try {
      const resolvedPath = snapshotPath(scope)
      const tmpPath = tmpSnapshotPath(scope)
      await ensureDirectory()
      // Write temp first to reduce chance of partial-file corruption.
      await atomicWriteJson(tmpPath, snapshot)
      await atomicWriteJson(resolvedPath, snapshot)
      return true
    } catch (error) {
      console.warn('Failed to save local state snapshot:', error)
      return false
    }
  }
}

export default localStateService
