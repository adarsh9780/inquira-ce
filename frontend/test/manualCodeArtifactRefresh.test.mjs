import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('manual code execution refreshes artifact panes without reloading the turn', () => {
  const codeTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'),
    'utf-8',
  )

  assert.equal(codeTabSource.includes('appStore.refreshActiveTurnArtifacts()'), true)
  assert.equal(codeTabSource.includes('appStore.loadActiveTurnRelations('), false)
  assert.equal(codeTabSource.includes('appStore.setScalars(viewModel.scalars)'), true)
  assert.equal(codeTabSource.includes('appStore.setSelectedTableArtifact(workspaceId, viewModel.dataframes[0]?.data?.artifact_id || \'\')'), true)
  assert.equal(codeTabSource.includes('appStore.setSelectedFigureArtifact(workspaceId, viewModel.figures[0]?.artifact_id || \'\')'), true)
})
