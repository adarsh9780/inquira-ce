const DB_NAME = 'inquira-file-handles'
const STORE_NAME = 'handles'
const ACTIVE_HANDLE_KEY = 'active_dataset'

function supportsIndexedDb() {
  return typeof window !== 'undefined' && typeof window.indexedDB !== 'undefined'
}

function openDb() {
  return new Promise((resolve, reject) => {
    if (!supportsIndexedDb()) {
      resolve(null)
      return
    }

    const request = window.indexedDB.open(DB_NAME, 1)

    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }

    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function saveActiveFileHandle(handle, meta = {}) {
  const db = await openDb()
  if (!db) return false

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).put(
      {
        handle,
        meta,
        updated_at: new Date().toISOString()
      },
      ACTIVE_HANDLE_KEY
    )
    tx.oncomplete = () => {
      db.close()
      resolve(true)
    }
    tx.onerror = () => {
      db.close()
      reject(tx.error)
    }
  })
}

export async function getActiveFileHandleRecord() {
  const db = await openDb()
  if (!db) return null

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const request = tx.objectStore(STORE_NAME).get(ACTIVE_HANDLE_KEY)
    request.onsuccess = () => {
      db.close()
      resolve(request.result || null)
    }
    request.onerror = () => {
      db.close()
      reject(request.error)
    }
  })
}

export async function clearActiveFileHandle() {
  const db = await openDb()
  if (!db) return false

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).delete(ACTIVE_HANDLE_KEY)
    tx.oncomplete = () => {
      db.close()
      resolve(true)
    }
    tx.onerror = () => {
      db.close()
      reject(tx.error)
    }
  })
}
