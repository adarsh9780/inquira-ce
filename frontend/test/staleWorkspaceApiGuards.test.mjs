import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('artifact panels guard native calls until the active turn and workspace are valid', () => {
  const tableTab = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )
  const figureTab = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )
  assert.equal(tableTab.includes('if (!conversationId || !turnId || !workspaceStore.hasWorkspace)'), true)
  assert.equal(tableTab.includes('if (!workspaceId || !normalizedArtifactId || (!sourceArtifactId && (!conversationId || !turnId))) return'), true)
  assert.equal(figureTab.includes('if (!conversationId || !turnId || !workspaceStore.hasWorkspace)'), true)
  assert.equal(figureTab.includes('if (!normalizedArtifactId || !workspaceStore.hasWorkspace)'), true)
  assert.equal(figureTab.includes('if (!conversationId || !turnId) {'), true)
})
