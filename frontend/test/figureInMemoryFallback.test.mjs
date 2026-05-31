import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure tab does not use in-memory figure fallback for saved turn artifacts', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes("const MEMORY_FIGURE_PREFIX = 'memory:'"), false)
  assert.equal(source.includes('const inMemoryFigureArtifacts = computed(() => {'), false)
  assert.equal(source.includes('if (isMemoryFigureId(normalizedArtifactId)) {'), false)
  assert.equal(source.includes('memory_figure: normalizedFigure'), false)
  assert.equal(source.includes('(memory)'), false)
  assert.equal(source.includes('apiService.v1GetTurnArtifactMetadata('), true)
})
