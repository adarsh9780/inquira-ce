import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure tab prefers latest generated artifact hint when refreshing chart list', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function resolveLatestFigureHint() {'), true)
  assert.equal(source.includes('function pickPreferredArtifactId(artifacts, preferredArtifactId, preferredLogicalName) {'), true)
  assert.equal(source.includes('preferredArtifactId: latestFigureHint.artifactId'), true)
  assert.equal(source.includes('const nextSelection = preferredArtifactId'), true)
})
