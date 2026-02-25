import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists local session snapshot via Tauri app data file service', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes("import { localStateService } from '../services/localStateService'"), true)
  assert.equal(source.includes('buildLocalStateSnapshot()'), true)
  assert.equal(source.includes('await localStateService.saveSnapshot(buildLocalStateSnapshot())'), true)
  assert.equal(source.includes('await localStateService.loadSnapshot()'), true)
})

test('local snapshot writer is compatible when Tauri file handle has no sync method', () => {
  const servicePath = resolve(process.cwd(), 'src/services/localStateService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes("if (typeof file.sync === 'function')"), true)
})

test('app boot and unload flows load and flush local snapshot state', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('await appStore.loadLocalConfig()'), true)
  assert.equal(source.includes('void appStore.flushLocalConfig?.()'), true)
})

test('tauri fs capability allows writing local snapshot into app data scope', () => {
  const capPath = resolve(process.cwd(), '../src-tauri/capabilities/default.json')
  const raw = readFileSync(capPath, 'utf-8')
  const capability = JSON.parse(raw)
  const permissions = capability?.permissions || []

  assert.equal(Array.isArray(permissions), true)
  assert.equal(permissions.includes('fs:create-app-specific-dirs'), true)
  assert.equal(permissions.includes('fs:allow-appdata-read-recursive'), true)
  assert.equal(permissions.includes('fs:allow-appdata-write-recursive'), true)
})
