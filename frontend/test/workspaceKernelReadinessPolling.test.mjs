import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace runtime readiness is observed without store-owned bootstrap polling', () => {
  const store = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')
  const statusBar = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')
  const chatInput = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(store.includes('function waitForWorkspaceRuntimeReady('), false)
  assert.equal(store.includes('function ensureWorkspaceRuntimeReady('), false)
  assert.equal(store.includes('function setWorkspaceRuntimeStatus(workspaceId, status)'), true)
  assert.equal(store.includes('function getWorkspaceRuntimeStatus(workspaceId = activeWorkspaceId.value)'), true)
  assert.equal(statusBar.includes('async function refreshWorkspaceRuntimeStatusFromApi('), true)
  assert.equal(statusBar.includes('apiService.v1GetWorkspaceRuntimeStatus(normalizedWorkspaceId)'), true)
  assert.equal(chatInput.includes('async function refreshRuntimeStatusAfterExplicitWork(workspaceId)'), true)
})
