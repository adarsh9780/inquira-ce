import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists local session snapshots through the desktop state service', () => {
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
  assert.equal(source.includes('selected_coding_model: selectedModel.value || \'\''), true)
  assert.equal(source.includes('slow_request_warning_seconds: normalizeSlowRequestWarningSeconds(slowRequestWarningSeconds.value)'), true)
  assert.equal(source.includes('active_turn_id: activeTurnId.value || \'\''), true)
  assert.equal(source.includes('enabled_models: Array.isArray(providerMainModels.value) ? [...providerMainModels.value] : []'), false)
  assert.equal(source.includes('terminal_open: !!isTerminalOpen.value'), true)
  assert.equal(source.includes('terminal_consent_granted: !!terminalConsentGranted.value'), true)
  assert.equal(source.includes('if (typeof ui.terminal_open === \'boolean\')'), true)
  assert.equal(source.includes('if (typeof ui.terminal_consent_granted === \'boolean\')'), true)
  assert.equal(source.includes('terminalConsentGranted.value = ui.terminal_consent_granted'), true)
})

test('app boot and unload flows load and flush local snapshot state', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('await appStore.loadLocalConfig(userId)'), true)
  assert.equal(source.includes('appStore.resetForAuthBoundary()'), true)
  assert.equal(source.includes('void appStore.flushLocalConfig?.()'), true)
  assert.equal(source.includes("window.addEventListener('beforeunload', handleAppUnload)"), true)
  assert.equal(source.includes('e.preventDefault()'), false)
  assert.equal(source.includes("e.returnValue = ''"), false)
})

test('terminal pane visibility and execution consent are persisted to local snapshot', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('function toggleTerminal() {'), true)
  assert.equal(source.includes('isTerminalOpen.value = !isTerminalOpen.value'), true)
  assert.equal(source.includes('function setTerminalConsentGranted(granted) {'), true)
  assert.equal(source.includes('terminalConsentGranted.value = !!granted'), true)
  assert.equal(source.includes('saveLocalConfig()'), true)
})

test('local snapshot restore recovers model selections and flushes pending preference sync on app close', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('const llm = snapshot.llm || {}'), true)
  assert.equal(source.includes('const snapshotProvider = llmProvider.value || DEFAULT_PROVIDER'), true)
  assert.equal(source.includes('const restoredMainModels = normalizeModelList(llm.provider_main_models, snapshotProvider)'), true)
  assert.equal(source.includes('if (typeof llm.selected_model === \'string\' && llm.selected_model.trim())'), true)
  assert.equal(source.includes('if (typeof llm.selected_lite_model === \'string\' && llm.selected_lite_model.trim())'), true)
  assert.equal(source.includes('if (typeof sessionState.active_turn_id === \'string\')'), true)
  assert.equal(source.includes('selectedCodingModel.value = selectedModel.value || selectedCodingModel.value'), true)
  assert.equal(source.includes('if (llm.slow_request_warning_seconds !== undefined && llm.slow_request_warning_seconds !== null)'), true)
  assert.equal(source.includes('if (preferenceSyncTimer) {'), true)
  assert.equal(source.includes('await syncPreferencesNow(targetUserId)'), true)
})

test('remote preference sync excludes local-only and unsupported fields', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')
  const start = source.indexOf('async function syncPreferencesNow(targetUserId) {')
  const end = source.indexOf('async function loadLocalConfig(', start)
  const syncBlock = source.slice(start, end)

  assert.equal(syncBlock.includes('selected_model: selectedModel.value'), true)
  assert.equal(syncBlock.includes('selected_coding_model: selectedModel.value'), true)
  assert.equal(syncBlock.includes('enabled_models:'), false)
  assert.equal(syncBlock.includes('schema_context:'), false)
  assert.equal(syncBlock.includes('terminal_risk_acknowledged:'), false)
  assert.equal(syncBlock.includes('active_workspace_id:'), false)
  assert.equal(syncBlock.includes('ui_theme:'), false)
})
