import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab completion source supports full token matching, explicit trigger, and ingested fallback', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("context.matchBefore(/[A-Za-z_][\\w.\\[\\]\"']*/)"), true)
  assert.equal(source.includes('if (!word) {'), true)
  assert.equal(source.includes('if (!context.explicit) return null'), true)
  assert.equal(source.includes('from: context.pos'), true)
  assert.equal(source.includes('Array.isArray(appStore.ingestedColumns)'), true)
  assert.equal(source.includes('String(appStore.ingestedTableName || \'\').trim()'), true)
  assert.equal(source.includes("validFor: /^[A-Za-z_][\\w.\\[\\]\"']*$/"), true)
  assert.equal(source.includes('await appStore.fetchColumnCatalog({ force: true })'), true)
})
