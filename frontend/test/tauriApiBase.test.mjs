import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service resolves Tauri backend base via get_backend_url command', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (window.__TAURI_INTERNALS__)'), true)
  assert.equal(source.includes("invoke('get_backend_url')"), true)
  assert.equal(source.includes('window.__INQUIRA_API_BASE__'), true)
})
