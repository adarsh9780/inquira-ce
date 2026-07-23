import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab completion source supports full token matching and catalog-backed suggestions', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("context.matchBefore(/[A-Za-z_][\\w.\\[\\]\"']*/)"), true)
  assert.equal(source.includes('if (!word) {'), true)
  assert.equal(source.includes('if (!context.explicit) return null'), true)
  assert.equal(source.includes('from: context.pos'), true)
  assert.equal(source.includes('Array.isArray(appStore.columnCatalog)'), true)
  assert.equal(source.includes('appStore.activeWorkspaceSummary?.table_names'), true)
  assert.equal(source.includes('appStore.ingestedColumns'), false)
  assert.equal(source.includes('appStore.ingestedTableName'), false)
  assert.equal(source.includes("validFor: /^[A-Za-z_][\\w.\\[\\]\"']*$/"), true)
  assert.equal(source.includes('await appStore.fetchColumnCatalog({ force: true })'), false)
})
