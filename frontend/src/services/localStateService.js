import {
  BaseDirectory,
  create,
  exists,
  mkdir,
  readTextFile
} from '@tauri-apps/plugin-fs'

const SNAPSHOT_DIR = 'state'
const SNAPSHOT_FILE = `${SNAPSHOT_DIR}/session_state.json`
const TMP_FILE = `${SNAPSHOT_FILE}.tmp`

function isTauriRuntime() {
  return typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
}

async function ensureDirectory() {
  await mkdir(SNAPSHOT_DIR, { baseDir: BaseDirectory.AppData, recursive: true })
}

async function atomicWriteJson(path, payload) {
  const serialized = JSON.stringify(payload, null, 2)
  const file = await create(path, { baseDir: BaseDirectory.AppData })
  try {
    await file.write(new TextEncoder().encode(serialized))
    await file.sync()
  } finally {
    await file.close()
  }
}

export const localStateService = {
  async loadSnapshot() {
    if (!isTauriRuntime()) return null
    try {
      const fileExists = await exists(SNAPSHOT_FILE, { baseDir: BaseDirectory.AppData })
      if (!fileExists) return null
      const raw = await readTextFile(SNAPSHOT_FILE, { baseDir: BaseDirectory.AppData })
      if (!raw || !raw.trim()) return null
      return JSON.parse(raw)
    } catch (error) {
      console.warn('Failed to load local state snapshot:', error)
      return null
    }
  },

  async saveSnapshot(snapshot) {
    if (!isTauriRuntime()) return false
    try {
      await ensureDirectory()
      // Write temp first to reduce chance of partial-file corruption.
      await atomicWriteJson(TMP_FILE, snapshot)
      await atomicWriteJson(SNAPSHOT_FILE, snapshot)
      return true
    } catch (error) {
      console.warn('Failed to save local state snapshot:', error)
      return false
    }
  }
}

export default localStateService
