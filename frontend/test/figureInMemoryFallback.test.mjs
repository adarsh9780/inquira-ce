import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure tab supports in-memory figure fallback when persisted artifacts are unavailable', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes("const MEMORY_FIGURE_PREFIX = 'memory:'"), true)
  assert.equal(source.includes('const inMemoryFigureArtifacts = computed(() => {'), true)
  assert.equal(source.includes('if (isMemoryFigureId(normalizedArtifactId)) {'), true)
  assert.equal(source.includes('memory_figure: normalizedFigure'), true)
  assert.equal(source.includes('(memory)'), true)
})
