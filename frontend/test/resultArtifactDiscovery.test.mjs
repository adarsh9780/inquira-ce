import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('always-mounted results pane discovers table and chart counts before tabs open', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue'), 'utf-8')

  assert.equal(source.includes("artifactApi.listTurn(conversationId, turnId, 'dataframe'"), true)
  assert.equal(source.includes("artifactApi.listTurn(conversationId, turnId, 'figure'"), true)
  assert.equal(source.includes('catalogTableCount.value = tableCount'), true)
  assert.equal(source.includes('catalogChartCount.value = chartCount'), true)
  assert.equal(source.includes('artifactStore.setDataframeCount(tableCount)'), true)
  assert.equal(source.includes('artifactStore.setFigureCount(chartCount)'), true)
  assert.equal(source.includes("uiStore.setDataPane('figure')"), true)
  assert.equal(source.includes("uiStore.setDataPane('table')"), true)
  assert.equal(source.includes('artifactStore.activeTurnArtifactRefreshKey'), true)
  assert.equal(source.includes('artifactCatalogAbortController?.abort()'), true)
})
