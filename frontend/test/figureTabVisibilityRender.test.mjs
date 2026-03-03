import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure tab re-renders when data pane switches to figure', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('watch(() => appStore.dataPane'), true)
  assert.equal(source.includes("if (pane === 'figure' && selectedFigure.value)"), true)
  assert.equal(source.includes('watch(() => appStore.activeTab'), false)
})
