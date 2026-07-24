import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('manual code execution keeps current structured artifacts inside its run block', () => {
  const codeTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'),
    'utf-8',
  )

  assert.equal(codeTabSource.includes('appStore.refreshActiveTurnArtifacts()'), false)
  assert.equal(codeTabSource.includes('conversationStore.loadActiveTurnRelations('), false)
  assert.equal(codeTabSource.includes('variables: latestExpressionVariables(normalized)'), true)
  assert.equal(codeTabSource.includes('artifacts: normalized.artifacts'), true)
  assert.equal(codeTabSource.includes('artifacts: []'), false)
  assert.equal(codeTabSource.includes('tableOutputs = stampRunResults(viewModel.dataframes.slice(0, 1)'), true)
  assert.equal(codeTabSource.includes('chartOutputs = stampRunResults(viewModel.figures.slice(0, 1)'), true)
  assert.equal(codeTabSource.includes('scalarOutputs = stampRunResults(viewModel.scalars.slice(0, 1)'), true)
  assert.equal(codeTabSource.includes('artifactStore.setDataframes(dataframes)'), false)
  assert.equal(codeTabSource.includes('artifactStore.setFigures(figures)'), false)
})
