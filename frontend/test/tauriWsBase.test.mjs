import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('websocket service can resolve Tauri ws base from backend url command', () => {
  const servicePath = resolve(process.cwd(), 'src/services/websocketService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (window.__TAURI_INTERNALS__)'), true)
  assert.equal(source.includes('tauriWsBaseOverride'), true)
  assert.equal(source.includes("invoke('get_backend_url')"), true)
  assert.equal(source.includes('window.__INQUIRA_API_BASE__'), true)
  assert.equal(source.includes("return 'ws://127.0.0.1:8000'"), true)
})
