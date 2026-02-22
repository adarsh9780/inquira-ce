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

test('app boot and unload flows load and flush local snapshot state', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('await appStore.loadLocalConfig()'), true)
  assert.equal(source.includes('void appStore.flushLocalConfig?.()'), true)
})
