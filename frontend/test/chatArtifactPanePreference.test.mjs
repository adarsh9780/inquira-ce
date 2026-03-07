import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat artifact handling preserves active data pane preference and sorts artifacts newest-first', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/chat/ChatInput.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function sortArtifactsNewestFirst(items) {'), true)
  assert.equal(source.includes('const previousDataPane = String(appStore.dataPane || \'\').trim().toLowerCase()'), true)
  assert.equal(source.includes('const artifactItems = sortArtifactsNewestFirst(Array.isArray(response?.artifacts) ? response.artifacts : [])'), true)
  assert.equal(source.includes('if (previousDataPane === \'table\' && dataframeArtifacts.length > 0) {'), true)
  assert.equal(source.includes('} else if (previousDataPane === \'figure\' && figureArtifacts.length > 0) {'), true)
})
