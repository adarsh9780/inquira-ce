import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar and table tab use app store as the single kernel status source of truth', () => {
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
  assert.equal(tableTabSource.includes("if (appStore.getWorkspaceKernelStatus(normalizedWorkspaceId) === 'ready') {"), true)
  assert.equal(tableTabSource.includes('appStore.setWorkspaceKernelStatus(normalizedWorkspaceId, status)'), true)
  assert.equal(tableTabSource.includes('() => appStore.getWorkspaceKernelStatus(appStore.activeWorkspaceId)'), true)
})
