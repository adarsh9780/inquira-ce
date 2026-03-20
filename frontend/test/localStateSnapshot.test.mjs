import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists local session snapshot via Tauri app data file service', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes("import { localStateService } from '../services/localStateService'"), true)
  assert.equal(source.includes('buildLocalStateSnapshot()'), true)
  assert.equal(source.includes('localStateService.saveSnapshot(snapshot, targetUserId)'), true)
  assert.equal(source.includes('await localStateService.saveSnapshot(buildLocalStateSnapshot(), targetUserId)'), true)
  assert.equal(source.includes('await localStateService.loadSnapshot(targetUserId)'), true)
  assert.equal(source.includes('llm: {'), true)
  assert.equal(source.includes('selected_model: selectedModel.value || \'\''), true)
  assert.equal(source.includes('selected_lite_model: selectedLiteModel.value || \'\''), true)
  assert.equal(source.includes('selected_coding_model: selectedCodingModel.value || \'\''), true)
  assert.equal(source.includes('enabled_models: Array.isArray(availableModels.value) ? [...availableModels.value] : []'), true)
  assert.equal(source.includes('terminal_open: !!isTerminalOpen.value'), true)
  assert.equal(source.includes('if (typeof ui.terminal_open === \'boolean\')'), true)
})

test('local snapshot writer is compatible when Tauri file handle has no sync method', () => {
  const servicePath = resolve(process.cwd(), 'src/services/localStateService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes("if (typeof file.sync === 'function')"), true)
  assert.equal(source.includes('function snapshotPath(scope) {'), true)
  assert.equal(source.includes('session_state_${key}.json'), true)
  assert.equal(source.includes('normalizeScope(scope)'), true)
})

test('app boot and unload flows load and flush local snapshot state', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('await appStore.loadLocalConfig(userId)'), true)
  assert.equal(source.includes('appStore.resetForAuthBoundary()'), true)
  assert.equal(source.includes('void appStore.flushLocalConfig?.()'), true)
})

test('terminal pane visibility changes are persisted to local snapshot', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('function toggleTerminal() {'), true)
  assert.equal(source.includes('isTerminalOpen.value = !isTerminalOpen.value'), true)
  assert.equal(source.includes('saveLocalConfig()'), true)
})

test('local snapshot restore recovers model selections and flushes pending preference sync on app close', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('const llm = snapshot.llm || {}'), true)
  assert.equal(source.includes('if (typeof llm.selected_model === \'string\' && llm.selected_model.trim())'), true)
  assert.equal(source.includes('if (typeof llm.selected_lite_model === \'string\' && llm.selected_lite_model.trim())'), true)
  assert.equal(source.includes('if (typeof llm.selected_coding_model === \'string\' && llm.selected_coding_model.trim())'), true)
  assert.equal(source.includes('if (preferenceSyncTimer) {'), true)
  assert.equal(source.includes('await syncPreferencesNow(targetUserId)'), true)
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
