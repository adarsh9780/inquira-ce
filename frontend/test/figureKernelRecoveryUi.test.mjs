import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure pane reads saved turn charts without runtime recovery loop', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function isRuntimeAvailabilityErrorMessage(message) {'), false)
  assert.equal(source.includes("normalized.includes('requires an active workspace runtime')"), false)
  assert.equal(source.includes('async function recoverFigureStateAfterRuntimeReady() {'), false)
  assert.equal(source.includes('await apiService.v1GetWorkspaceRuntimeStatus(workspaceId)'), false)
  assert.equal(source.includes("if (status !== 'ready') return"), false)
  assert.equal(source.includes('await loadWorkspaceFigureArtifacts(workspaceId, {'), false)
  assert.equal(source.includes("() => [\n    String(appStore.activeConversationId || '').trim(),\n    String(appStore.activeTurnId || '').trim(),"), true)
  assert.equal(source.includes('await loadSelectedFigurePayload(nextSelection)'), true)
  assert.equal(source.includes("() => appStore.getWorkspaceRuntimeStatus(appStore.activeWorkspaceId)"), false)
  assert.equal(source.includes('apiService.v1ListTurnArtifacts('), true)
})
