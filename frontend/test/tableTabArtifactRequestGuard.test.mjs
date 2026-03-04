import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('TableTab serializes artifact requests and gates list fetch on kernel readiness', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'components', 'analysis', 'TableTab.vue')
  const source = fs.readFileSync(filePath, 'utf8')

  assert.equal(source.includes('function enqueueSerializedRequest(task)'), true)
  assert.equal(source.includes('async function waitForKernelReady(workspaceId, signal)'), true)
  assert.equal(source.includes('await waitForKernelReady(normalizedWorkspaceId, listAbortController.signal)'), true)
  assert.equal(source.includes('watch(() => appStore.dataframes.length'), false)
  assert.equal(source.includes('params.failCallback()'), false)
  assert.equal(source.includes('`infinite-${selectedArtifactId}-${datasourceVersion}`'), false)
  assert.equal(source.includes('const datasourceVersion = ref('), false)
  assert.equal(source.includes('function columnsChanged(nextColumns)'), true)
  assert.equal(source.includes('if (columnsChanged(nextColumns)) {'), true)
})
