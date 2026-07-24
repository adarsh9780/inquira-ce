import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails exports use the native Go save dialog', () => {
  const service = read('src/utils/exportFile.ts')
  const goApp = read('../app.go')

  assert.equal(service.includes('app?.SaveExportFile'), true)
  assert.equal(service.includes('bytesToBase64'), true)
  assert.equal(service.includes('content_base64'), true)
  assert.equal(goApp.includes('func (a *App) SaveExportFile(request desktop.ExportRequest) (bool, error)'), true)
})

test('native export preserves user cancellation instead of falling through to a browser download', () => {
  const service = read('src/utils/exportFile.ts')

  assert.equal(service.includes('return Boolean(await app.SaveExportFile'), true)
  assert.equal(service.includes("console.error('Failed to save export through Wails:'"), true)
})
