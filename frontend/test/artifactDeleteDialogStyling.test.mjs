import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table and figure toolbars use shared input/button primitives to match modal styling', () => {
  const tablePath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const figurePath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')

  const tableSource = readFileSync(tablePath, 'utf-8')
  const figureSource = readFileSync(figurePath, 'utf-8')

  assert.equal(tableSource.includes('class="input-base h-8 pl-8 pr-2"'), true)
  assert.equal(tableSource.includes('class="btn-icon h-8 w-8 shrink-0 border"'), true)
  assert.equal(tableSource.includes('style="border-color: var(--color-border); color: var(--color-text-muted);"'), true)

  assert.equal(figureSource.includes('class="btn-icon h-8 w-8 shrink-0 border"'), true)
  assert.equal(figureSource.includes('style="border-color: var(--color-border); color: var(--color-text-muted);"'), true)
})
