import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service uses http backend base in packaged Tauri mode', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (window.__TAURI_INTERNALS__)'), true)
  assert.equal(source.includes("return 'http://localhost:8000'"), true)
  assert.equal(source.includes('return window.location.origin'), false)
})
