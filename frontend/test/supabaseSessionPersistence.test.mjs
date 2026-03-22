import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('desktop supabase auth uses a tauri-backed storage adapter for persisted sessions', () => {
  const authSource = readFileSync(
    resolve(process.cwd(), 'src/services/supabaseAuthService.js'),
    'utf-8',
  )
  const storageSource = readFileSync(
    resolve(process.cwd(), 'src/services/supabaseStorageService.js'),
    'utf-8',
  )

  assert.equal(authSource.includes("import { tauriSupabaseStorage } from './supabaseStorageService'"), true)
  assert.equal(authSource.includes('storage: isTauriDesktop ? tauriSupabaseStorage : undefined'), true)
  assert.equal(authSource.includes('userStorage: isTauriDesktop ? tauriSupabaseStorage : undefined'), true)
  assert.equal(storageSource.includes("const STORAGE_PATH = `${STORAGE_DIR}/supabase_auth_storage.json`"), true)
  assert.equal(storageSource.includes('BaseDirectory.AppData'), true)
  assert.equal(storageSource.includes('async getItem(key)'), true)
  assert.equal(storageSource.includes('async setItem(key, value)'), true)
  assert.equal(storageSource.includes('async removeItem(key)'), true)
})
