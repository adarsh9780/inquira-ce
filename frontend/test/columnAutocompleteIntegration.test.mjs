import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input includes column suggestion dropdown integration', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes("import ColumnSuggest from './ColumnSuggest.vue'"), true)
  assert.equal(source.includes('<ColumnSuggest'), true)
  assert.equal(source.includes('appStore.fetchColumnCatalog'), true)
  assert.equal(source.includes('acceptColumnSuggestion'), true)
})

test('code tab uses appStore column catalog in custom completion source', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('function completionSource(context)'), true)
  assert.equal(source.includes('autocompletion({ override: [completionSource] })'), true)
  assert.equal(source.includes('Array.isArray(appStore.columnCatalog)'), true)
  assert.equal(source.includes('await appStore.fetchColumnCatalog({ force: true })'), true)
})
