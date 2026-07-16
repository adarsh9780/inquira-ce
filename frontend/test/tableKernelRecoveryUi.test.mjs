import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table pane reads saved turn artifacts without kernel readiness recovery loop', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(tableTabPath, 'utf-8')

  assert.equal(source.includes('function isKernelReadinessTimeoutMessage(message) {'), false)
  assert.equal(source.includes("Kernel did not become ready in 120 seconds"), false)
  assert.equal(source.includes('async function recoverTableStateAfterKernelReady() {'), false)
  assert.equal(source.includes("if (status !== 'ready') return"), false)
  assert.equal(source.includes('await loadWorkspaceArtifacts(workspaceId)'), false)
  assert.equal(source.includes('function startKernelRecoveryPolling() {'), false)
  assert.equal(source.includes('kernelRecoveryPoller = setInterval(() => {'), false)
  assert.equal(source.includes('apiService.v1ListTurnArtifacts('), true)
  assert.equal(source.includes('apiService.getTurnDataframeArtifactRows('), true)
})
