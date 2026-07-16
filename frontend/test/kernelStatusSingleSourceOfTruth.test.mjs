import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar owns runtime status while table tab reads saved artifacts without runtime gating', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )
  const tableTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(statusBarSource.includes("const runtimeStatus = ref('missing')"), false)
  assert.equal(statusBarSource.includes('const workspaceRuntimeStatus = computed(() => appStore.activeWorkspaceRuntimeStatus)'), true)
  assert.equal(statusBarSource.includes('appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, status)'), true)

  assert.equal(tableTabSource.includes('runtimeReadyWorkspaceId'), false)
  assert.equal(tableTabSource.includes('appStore.getWorkspaceRuntimeStatus'), false)
  assert.equal(tableTabSource.includes('appStore.setWorkspaceRuntimeStatus'), false)
  assert.equal(tableTabSource.includes('apiService.v1GetWorkspaceRuntimeStatus'), false)
  assert.equal(tableTabSource.includes('apiService.v1ListTurnArtifacts('), true)
})
