import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('manual code execution keeps structured artifacts inside its run block', () => {
  const codeTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'),
    'utf-8',
  )

  assert.equal(codeTabSource.includes('appStore.refreshActiveTurnArtifacts()'), false)
  assert.equal(codeTabSource.includes('appStore.loadActiveTurnRelations('), false)
  assert.equal(codeTabSource.includes('tableOutputs = stampRunResults(orderedViewModel.dataframes'), true)
  assert.equal(codeTabSource.includes('chartOutputs = stampRunResults(orderedViewModel.figures'), true)
  assert.equal(codeTabSource.includes('scalarOutputs = stampRunResults(orderedViewModel.scalars'), true)
  assert.equal(codeTabSource.includes('appStore.setDataframes(dataframes)'), false)
  assert.equal(codeTabSource.includes('appStore.setFigures(figures)'), false)
})
