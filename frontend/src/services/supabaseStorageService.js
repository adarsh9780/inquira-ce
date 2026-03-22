import {
  BaseDirectory,
  create,
  exists,
  mkdir,
  readTextFile,
} from '@tauri-apps/plugin-fs'

const STORAGE_DIR = 'state'
const STORAGE_PATH = `${STORAGE_DIR}/supabase_auth_storage.json`

function isTauriRuntime() {
  return typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__
}

async function ensureDirectory() {
  await mkdir(STORAGE_DIR, { baseDir: BaseDirectory.AppData, recursive: true })
}

async function readStorageMap() {
  if (!isTauriRuntime()) return {}

  try {
    const fileExists = await exists(STORAGE_PATH, { baseDir: BaseDirectory.AppData })
    if (!fileExists) return {}
    const raw = await readTextFile(STORAGE_PATH, { baseDir: BaseDirectory.AppData })
    if (!raw || !raw.trim()) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (error) {
    console.warn('Failed to read persisted Supabase auth storage:', error)
    return {}
  }
}

async function writeStorageMap(payload) {
  if (!isTauriRuntime()) return

  try {
    await ensureDirectory()
    const file = await create(STORAGE_PATH, { baseDir: BaseDirectory.AppData })
    try {
      await file.write(new TextEncoder().encode(JSON.stringify(payload, null, 2)))
      if (typeof file.sync === 'function') {
        await file.sync()
      }
    } finally {
      await file.close()
    }
  } catch (error) {
    console.warn('Failed to persist Supabase auth storage:', error)
  }
}

export const tauriSupabaseStorage = {
  async getItem(key) {
    const storage = await readStorageMap()
    const value = storage[String(key || '')]
    return typeof value === 'string' ? value : null
  },

  async setItem(key, value) {
    const storage = await readStorageMap()
    storage[String(key || '')] = String(value ?? '')
    await writeStorageMap(storage)
  },

  async removeItem(key) {
    const storage = await readStorageMap()
    delete storage[String(key || '')]
    await writeStorageMap(storage)
  },
}

export default tauriSupabaseStorage
