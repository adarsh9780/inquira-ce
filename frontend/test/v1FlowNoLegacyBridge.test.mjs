import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app bootstrap uses v1 workspace state instead of legacy settings bootstrap', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('await appStore.fetchWorkspaces()'), true)
  assert.equal(source.includes('apiService.getSettings()'), false)
  assert.equal(source.includes('apiService.loadSchema('), false)
})

test('chat submit path enforces workspace dataset sync without legacy setDataPath bridge', () => {
  const chatPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatPath, 'utf-8')

  assert.equal(source.includes('async function ensureWorkspaceForChat()'), false)
  assert.equal(source.includes('const workspaceId = appStore.activeWorkspaceId'), true)
  assert.equal(source.includes('await ensureWorkspaceDatasetReady(workspaceId)'), true)
  assert.equal(source.includes('ensureBackendSchemaReadyForChat'), false)
  assert.equal(source.includes('apiService.setDataPathSimple('), false)
  assert.equal(source.includes('apiService.analyzeDataStream('), false)
  assert.equal(source.includes('apiService.analyzeData('), false)
})

test('v1 runtime avoids legacy settings check-update endpoint calls', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('checkUpdateNeededSettingsCheckUpdateGet'), false)
  assert.equal(source.includes('should_update: false'), true)
})
