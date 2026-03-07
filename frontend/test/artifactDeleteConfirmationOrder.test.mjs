import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table and figure delete flows await confirmation before delete API calls', () => {
  const tablePath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const figurePath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')

  const tableSource = readFileSync(tablePath, 'utf-8')
  const figureSource = readFileSync(figurePath, 'utf-8')

  assert.equal(tableSource.includes('async function resolveConfirmation(message) {'), true)
  assert.equal(tableSource.includes('const confirmed = await resolveConfirmation(`Delete table "${artifactLabel}"? This cannot be undone.`)'), true)
  assert.equal(tableSource.includes('await apiService.v1DeleteWorkspaceArtifact(workspaceId, artifactId)'), true)
  assert.equal(tableSource.includes('type="button"'), true)

  assert.equal(figureSource.includes('async function resolveConfirmation(message) {'), true)
  assert.equal(figureSource.includes('const confirmed = await resolveConfirmation(`Delete chart "${logicalName}"? This cannot be undone.`)'), true)
  assert.equal(figureSource.includes('await apiService.v1DeleteWorkspaceArtifact(workspaceId, artifactId)'), true)
  assert.equal(figureSource.includes('type="button"'), true)
})
