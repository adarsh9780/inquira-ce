import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure pane clears stale kernel-required banner after kernel becomes ready', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function isKernelAvailabilityErrorMessage(message) {'), true)
  assert.equal(source.includes("normalized.includes('requires an active workspace kernel')"), true)
  assert.equal(source.includes('async function recoverFigureStateAfterKernelReady() {'), true)
  assert.equal(source.includes('await apiService.v1GetWorkspaceKernelStatus(workspaceId)'), true)
  assert.equal(source.includes("if (status !== 'ready') return"), true)
  assert.equal(source.includes('await loadWorkspaceFigureArtifacts(workspaceId, {'), true)
  assert.equal(source.includes("() => appStore.getWorkspaceKernelStatus(appStore.activeWorkspaceId)"), true)
  assert.equal(source.includes("if (status === 'ready' && appStore.dataPane === 'figure') {"), true)
})
