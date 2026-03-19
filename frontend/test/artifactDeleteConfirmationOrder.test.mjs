import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table and figure delete flows use shared confirmation modal before delete API calls', () => {
  const tablePath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const figurePath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')

  const tableSource = readFileSync(tablePath, 'utf-8')
  const figureSource = readFileSync(figurePath, 'utf-8')

  assert.equal(tableSource.includes('ConfirmationModal'), true)
  assert.equal(tableSource.includes('window.confirm'), false)
  assert.equal(tableSource.includes('@click="openDeleteDialog"'), true)
  assert.equal(tableSource.includes('const deleteDialogMessage = computed(() => {'), true)
  assert.equal(tableSource.includes('await apiService.v1DeleteWorkspaceArtifact(workspaceId, artifactId)'), true)
  assert.equal(tableSource.includes('type="button"'), true)

  assert.equal(figureSource.includes('ConfirmationModal'), true)
  assert.equal(figureSource.includes('window.confirm'), false)
  assert.equal(figureSource.includes('@click="openDeleteDialog"'), true)
  assert.equal(figureSource.includes('const deleteDialogMessage = computed(() => {'), true)
  assert.equal(figureSource.includes('await apiService.v1DeleteWorkspaceArtifact(workspaceId, artifactId)'), true)
  assert.equal(figureSource.includes('type="button"'), true)
})
