import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure tab selects from the refreshed active turn chart list', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function resolveLatestFigureHint() {'), false)
  assert.equal(source.includes('function pickPreferredArtifactId(artifacts, preferredArtifactId, preferredLogicalName) {'), false)
  assert.equal(source.includes('preferredArtifactId: latestFigureHint.artifactId'), false)
  assert.equal(source.includes('const nextSelection = (hasExistingSelection ? selectedArtifactId.value : null)'), true)
  assert.equal(source.includes('|| candidates[0].artifact_id'), true)
})
