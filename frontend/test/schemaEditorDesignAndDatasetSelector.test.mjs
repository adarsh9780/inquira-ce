import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('schema editor follows shared UI language and supports dataset dropdown, descriptions, and aliases', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('v-model="selectedDatasetTable"'), true)
  assert.equal(source.includes('placeholder="Select dataset"'), true)
  assert.equal(source.includes('LLM Context Hint (Recommended)'), true)
  assert.equal(source.includes('This helps the LLM generate better analysis.'), true)
  assert.equal(source.includes('rows="2"'), true)
  assert.equal(source.includes('Enter one or more lines to describe this column'), true)
  assert.equal(source.includes('Aliases'), true)
  assert.equal(source.includes('Comma-separated aliases...'), true)
  assert.equal(source.includes('<input'), true)
  assert.equal(source.includes("background-color: var(--color-base)"), true)
  assert.equal(source.includes("border-color: var(--color-border)"), true)
})
