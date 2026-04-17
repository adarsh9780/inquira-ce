import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('schema editor uses calm border-light design system and readable dataset labels', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes('label: datasetFriendlyName(item.tableName)'), true)
  assert.equal(source.includes("raw.replace(/__\\d{6,}(?=__|$)/g, '')"), true)

  assert.equal(source.includes('class="schema-top-bar relative z-10"'), true)
  assert.equal(source.includes('class="schema-context-card"'), true)
  assert.equal(source.includes('border-left: 3px solid var(--color-accent);'), true)

  assert.equal(source.includes('class="schema-table-header-row"'), true)
  assert.equal(source.includes('class="schema-row-header-cell" aria-label="Row"'), true)
  assert.equal(source.includes('class="schema-row group align-top"'), true)
  assert.equal(source.includes("i % 2 === 0 ? 'schema-row-odd' : 'schema-row-even'"), true)
  assert.equal(source.includes('.schema-row-odd {'), true)
  assert.equal(source.includes('.schema-row-even {'), true)
  assert.equal(source.includes('.schema-row:hover {'), true)

  assert.equal(source.includes('class="schema-column-cell"'), true)
  assert.equal(source.includes('font-family: var(--font-mono);'), true)
  assert.equal(source.includes('class="schema-alias-tag"'), true)
  assert.equal(source.includes('background: var(--color-base-muted);'), true)

  assert.equal(source.includes('class="schema-ghost-btn"'), true)
  assert.equal(source.includes('class="schema-save-btn"'), true)
  assert.equal(source.includes('background: var(--color-accent);'), true)
  assert.equal(source.includes('>#</th>'), false)
  assert.equal(source.includes('class="schema-scroll-area h-full overflow-auto"'), true)
  assert.equal(source.includes('.schema-scroll-area {'), true)
  assert.equal(source.includes('scrollbar-width: none;'), true)
  assert.equal(source.includes('.schema-scroll-area::-webkit-scrollbar {'), true)
  assert.equal(source.includes('width: 0;'), true)
})
