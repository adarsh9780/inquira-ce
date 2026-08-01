import test from 'node:test'
import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { readFileSync } from './sourceText.mjs'

const editor = readFileSync(resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue'), 'utf-8')
const browser = readFileSync(resolve(process.cwd(), 'src/components/schema/SchemaTableNavigator.vue'), 'utf-8')

test('workspace manager separates workspace sections from dataset selection', () => {
  assert.equal(editor.includes('aria-label="Workspace manager sections"'), true)
  assert.equal(editor.includes("{ value: 'data' as const, label: 'Data' }"), true)
  assert.equal(editor.includes("{ value: 'context' as const, label: 'Context' }"), true)
  assert.equal(editor.includes("activeWorkspaceSection === 'context'"), true)
  assert.equal(editor.includes("activeWorkspaceSection.value = selection.kind === 'workspace' ? 'context' : 'data'"), true)
  assert.equal(editor.includes('data-action="add-workspace-data"'), true)
  assert.equal(editor.includes('await dataSourcesRef.value?.chooseFile()'), true)
  assert.equal(editor.includes('sourceDrawerOpen.value = true'), true)
})

test('dataset browser makes interactive rows explicit and searchable', () => {
  assert.equal(browser.includes('aria-label="Dataset browser"'), true)
  assert.equal(browser.includes('placeholder="Search datasets"'), true)
  assert.equal(browser.includes('v-for="table in filteredTables"'), true)
  assert.equal(browser.includes('cursor-pointer'), true)
  assert.equal(browser.includes('focus-visible:ring-2'), true)
  assert.equal(browser.includes("border-[var(--color-accent)]"), true)
  assert.equal(browser.includes('Workspace context'), false)
})
