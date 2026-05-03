import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat artifact handling uses chart-first pane priority and sorts artifacts newest-first', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/chat/ChatInput.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function sortArtifactsNewestFirst(items) {'), true)
  assert.equal(source.includes('const artifactItems = sortArtifactsNewestFirst(Array.isArray(response?.artifacts) ? response.artifacts : [])'), true)
  assert.equal(source.includes('if (figureArtifacts.length > 0) {'), true)
  assert.equal(source.includes('appStore.revealArtifactsPane({ hasFigures: true })'), true)
  assert.equal(source.includes('appStore.revealArtifactsPane({ hasDataframes: true })'), true)
  assert.equal(source.includes('appStore.revealArtifactsPane({ hasOutput: true })'), true)
})
