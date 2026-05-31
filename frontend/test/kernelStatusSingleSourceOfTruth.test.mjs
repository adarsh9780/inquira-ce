import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar owns kernel status while table tab reads saved artifacts without kernel gating', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )
  const tableTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(statusBarSource.includes("const kernelStatus = ref('missing')"), false)
  assert.equal(statusBarSource.includes('const kernelStatus = computed(() => appStore.activeWorkspaceKernelStatus)'), true)
  assert.equal(statusBarSource.includes('appStore.setWorkspaceKernelStatus(normalizedWorkspaceId, status)'), true)

  assert.equal(tableTabSource.includes('kernelReadyWorkspaceId'), false)
  assert.equal(tableTabSource.includes('appStore.getWorkspaceKernelStatus'), false)
  assert.equal(tableTabSource.includes('appStore.setWorkspaceKernelStatus'), false)
  assert.equal(tableTabSource.includes('apiService.v1GetWorkspaceKernelStatus'), false)
  assert.equal(tableTabSource.includes('apiService.v1ListTurnArtifacts('), true)
})
