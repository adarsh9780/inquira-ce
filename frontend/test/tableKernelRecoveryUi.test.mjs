import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table pane retries after kernel readiness timeout and clears stale missing error when kernel recovers', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(tableTabPath, 'utf-8')

  assert.equal(source.includes('function isKernelReadinessTimeoutMessage(message) {'), true)
  assert.equal(source.includes("Kernel did not become ready in 120 seconds"), true)
  assert.equal(source.includes('async function recoverTableStateAfterKernelReady() {'), true)
  assert.equal(source.includes("if (status !== 'ready') return"), true)
  assert.equal(source.includes('appStore.clearDataPaneError()'), true)
  assert.equal(source.includes('await loadWorkspaceArtifacts(workspaceId)'), true)
  assert.equal(source.includes('await prepareArtifact(selectedId)'), true)
  assert.equal(source.includes('function startKernelRecoveryPolling() {'), true)
  assert.equal(source.includes('kernelRecoveryPoller = setInterval(() => {'), true)
})
