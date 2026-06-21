import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace runtime bootstrap waits for a ready or busy status before runtime calls continue', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('async function waitForWorkspaceRuntimeReady(workspaceId, { timeoutMs = 15000, pollMs = 250 } = {}) {'), true)
  assert.equal(source.includes('const payload = await apiService.v1GetWorkspaceRuntimeStatus(targetWorkspaceId)'), true)
  assert.equal(source.includes("if (status === 'ready' || status === 'busy') {"), true)
  assert.equal(source.includes("setWorkspaceRuntimeStatus(targetWorkspaceId, 'connecting')"), true)
  assert.equal(source.includes('const runtimeReady = await waitForWorkspaceRuntimeReady(targetWorkspaceId)'), true)
})
