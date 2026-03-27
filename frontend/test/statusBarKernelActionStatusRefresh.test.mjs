import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar refreshes kernel state from API after interrupt and restart actions', () => {
  const path = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function refreshKernelStatusFromApi(workspaceId, fallbackStatus = \'missing\') {'), true)
  assert.equal(source.includes('await apiService.v1GetWorkspaceKernelStatus(normalizedWorkspaceId)'), true)
  assert.equal(source.includes('await refreshKernelStatusFromApi(workspaceId, response?.reset ? \'ready\' : \'missing\')'), true)
  assert.equal(source.includes('await refreshKernelStatusFromApi(workspaceId, response?.reset ? \'starting\' : \'missing\')'), true)
  assert.equal(source.includes('await refreshKernelStatusFromApi(workspaceId, \'error\')'), true)
})
