import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { bytesToBase64 } from '../src/utils/exportEncoding.js'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails exports use the native Go save dialog before legacy desktop and browser fallbacks', () => {
  const service = read('src/utils/exportFile.js')
  const goApp = read('../app.go')

  assert.equal(service.includes('app?.SaveExportFile'), true)
  assert.equal(service.includes('bytesToBase64'), true)
  assert.equal(service.includes('content_base64'), true)
  assert.equal(service.indexOf('app?.SaveExportFile') < service.indexOf('window.__TAURI_INTERNALS__'), true)
  assert.equal(goApp.includes('func (a *App) SaveExportFile(request desktop.ExportRequest) (bool, error)'), true)
})

test('native export preserves user cancellation instead of falling through to a browser download', () => {
  const service = read('src/utils/exportFile.js')

  assert.equal(service.includes('return Boolean(await app.SaveExportFile'), true)
  assert.equal(service.includes("console.error('Failed to save export through Wails:'"), true)
})

test('native export encoding preserves large binary payloads without argument overflow', () => {
  const payload = new Uint8Array(200_000)
  for (let index = 0; index < payload.length; index += 1) payload[index] = index % 251
  const decoded = Buffer.from(bytesToBase64(payload), 'base64')

  assert.deepEqual(decoded, Buffer.from(payload))
  assert.equal(Buffer.from(bytesToBase64('Δ export'), 'base64').toString('utf8'), 'Δ export')
})
