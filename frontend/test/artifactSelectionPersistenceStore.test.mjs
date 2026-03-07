import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists selected table/figure artifacts per workspace', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('const selectedTableArtifactsByWorkspace = ref({})'), true)
  assert.equal(source.includes('const selectedFigureArtifactsByWorkspace = ref({})'), true)
  assert.equal(source.includes('table_selected_artifacts: selectedTableArtifactsByWorkspace.value || {}'), true)
  assert.equal(source.includes('figure_selected_artifacts: selectedFigureArtifactsByWorkspace.value || {}'), true)
  assert.equal(source.includes('function setSelectedTableArtifact(workspaceId, artifactId) {'), true)
  assert.equal(source.includes('function getSelectedTableArtifact(workspaceId) {'), true)
  assert.equal(source.includes('function setSelectedFigureArtifact(workspaceId, artifactId) {'), true)
  assert.equal(source.includes('function getSelectedFigureArtifact(workspaceId) {'), true)
})

test('table and figure tabs restore and persist selected artifacts through app store', () => {
  const tableSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/TableTab.vue'), 'utf-8')
  const figureSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'), 'utf-8')

  assert.equal(tableSource.includes('appStore.getSelectedTableArtifact(workspaceId)'), true)
  assert.equal(tableSource.includes('appStore.setSelectedTableArtifact(normalizedWorkspaceId, String(newId || \'\').trim())'), true)
  assert.equal(figureSource.includes('appStore.getSelectedFigureArtifact(workspaceId)'), true)
  assert.equal(figureSource.includes('appStore.setSelectedFigureArtifact(normalizedWorkspaceId, String(artifactId || \'\').trim())'), true)
})
