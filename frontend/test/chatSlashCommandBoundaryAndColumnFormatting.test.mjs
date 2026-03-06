import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat slash command suggestions are constrained to beginning of input', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes("const prefixBeforeToken = value.slice(0, range.start)"), true)
  assert.equal(source.includes('if (prefixBeforeToken.trim().length > 0)'), true)
  assert.equal(source.includes('token.startsWith(\'/\')'), true)
  assert.equal(source.includes('suggestionsOpenUp'), true)
  assert.equal(source.includes('updateSuggestionPlacement()'), true)
  assert.equal(source.includes(":class=\"suggestionsOpenUp ? 'bottom-full mb-2' : 'top-full mt-1'\""), true)
})

test('chat column autocomplete supports escaped bracket notation for special column names', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('function buildColumnReference(tableName, columnName)'), true)
  assert.equal(source.includes('function collectColumnCandidates()'), true)
  assert.equal(source.includes('appStore.ingestedColumns'), true)
  assert.equal(source.includes('appStore.ingestedTableName'), true)
  assert.equal(source.includes('return `${table}["${escapeQuotedString(column)}"]`'), true)
  assert.equal(source.includes('isSpecial: !isSimpleIdentifier(columnName)'), true)
  assert.equal(source.includes('selected.insertText'), true)
})

test('column suggestion UI highlights escaped/special column references', () => {
  const suggestPath = resolve(process.cwd(), 'src/components/chat/ColumnSuggest.vue')
  const source = readFileSync(suggestPath, 'utf-8')

  assert.equal(source.includes('item.displayText || `${item.table_name}.${item.column_name}`'), true)
  assert.equal(source.includes("item?.isSpecial ? 'color: #0284c7;'"), true)
  assert.equal(source.includes(":class=\"openUp ? 'bottom-full mb-2' : 'top-full mt-1'\""), true)
})

test('code tab completion source formats special columns with escaped bracket notation', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('function buildColumnReference(tableName, columnName)'), true)
  assert.equal(source.includes('return `${table}["${escapeQuotedString(column)}"]`'), true)
  assert.equal(source.includes("column (escaped)"), true)
})
