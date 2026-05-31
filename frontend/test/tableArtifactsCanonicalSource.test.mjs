import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab uses active turn artifact catalog as canonical source', () => {
  const path = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('const allArtifacts = computed(() => (Array.isArray(workspaceArtifacts.value) ? workspaceArtifacts.value : []))'), true)
  assert.equal(source.includes('async function loadActiveTurnArtifacts()'), true)
  assert.equal(source.includes('apiService.v1ListTurnArtifacts('), true)
  assert.equal(source.includes('apiService.getTurnDataframeArtifactRows('), true)
  assert.equal(source.includes('apiService.v1ListWorkspaceArtifacts('), false)
  assert.equal(source.includes('apiService.getDataframeArtifactRows('), false)
  assert.equal(source.includes('waitForKernelReady'), false)
  assert.equal(source.includes("() => [\n    String(appStore.activeConversationId || '').trim(),\n    String(appStore.activeTurnId || '').trim(),"), true)
  assert.equal(source.includes('await prepareArtifact(nextSelection)'), true)
  assert.equal(source.includes('if (selectedArtifactId.value && !list.some((item) => item.artifact_id === selectedArtifactId.value))'), true)
})
