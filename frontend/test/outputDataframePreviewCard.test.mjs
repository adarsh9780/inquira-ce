import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('output tab renders notebook-style dataframe preview card with middle truncation and scroll container', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes("const PREVIEW_HEAD_ROWS = 8"), true)
  assert.equal(source.includes("const PREVIEW_TAIL_ROWS = 8"), true)
  assert.equal(source.includes("const PREVIEW_HEAD_COLUMNS = 5"), true)
  assert.equal(source.includes("const PREVIEW_TAIL_COLUMNS = 4"), true)
  assert.equal(source.includes('class="max-h-72 overflow-auto"'), true)
  assert.equal(source.includes("label: '...'"), true)
  assert.equal(source.includes("indexLabel: '...'"), true)
  assert.equal(source.includes('No row preview captured for this dataframe yet.'), true)
  assert.equal(source.includes('buildDataframePreview(item?.data)'), true)
})
