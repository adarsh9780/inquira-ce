import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails session snapshots load and save through the native Go bridge', () => {
  const service = read('src/services/localStateService.js')
  const goApp = read('../app.go')

  assert.equal(service.includes('app?.LoadLocalState'), true)
  assert.equal(service.includes('return await app.LoadLocalState(scope)'), true)
  assert.equal(service.includes('app?.SaveLocalState'), true)
  assert.equal(service.includes('return Boolean(await app.SaveLocalState(scope, snapshot))'), true)
  assert.equal(goApp.includes('func (a *App) LoadLocalState(scope string) (localstate.Snapshot, error)'), true)
  assert.equal(goApp.includes('func (a *App) SaveLocalState(scope string, snapshot localstate.Snapshot) (bool, error)'), true)
  assert.equal(read('../internal/localstate/repository.go').includes('type Snapshot = map[string]any'), true)
})

test('Wails snapshot failures remain best effort without falling through to Tauri files', () => {
  const service = read('src/services/localStateService.js')

  assert.equal(service.indexOf('app?.LoadLocalState') < service.indexOf('if (!isTauriRuntime())'), true)
  assert.equal(service.includes("console.warn('Failed to load local state snapshot through Wails:'"), true)
  assert.equal(service.includes("console.warn('Failed to save local state snapshot through Wails:'"), true)
})
