import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('websocket service uses ws://localhost:8000 in packaged Tauri mode', () => {
  const servicePath = resolve(process.cwd(), 'src/services/websocketService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (window.__TAURI_INTERNALS__)'), true)
  assert.equal(source.includes("return 'ws://localhost:8000'"), true)
  assert.equal(source.includes('return `${scheme}//${window.location.host}`'), true)
})
