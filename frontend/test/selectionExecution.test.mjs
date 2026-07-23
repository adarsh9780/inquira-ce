import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code editor binds Shift+Enter to selected code execution', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("key: 'Shift-Enter'"), true)
  assert.equal(source.includes('runSelectedCode()'), true)
  assert.equal(source.includes('getSelectedSnippet()'), true)
  assert.equal(source.includes('if (!range.empty)'), true)
  assert.equal(source.includes('editor.state.doc.lineAt(range.head)'), true)
  assert.equal(source.includes('preserveActiveTabOnNoOutput: true'), false)
  assert.equal(source.includes("appStore.setDataPane('output')"), true)
  assert.equal(source.includes("appStore.setActiveTab('output')"), true)
  assert.equal(source.includes('function startRunEntry(scopeLabel, code) {'), true)
  assert.equal(source.includes("command: String(code || '')"), true)
  assert.equal(source.includes("status: 'running'"), true)
  assert.equal(source.includes('appStore.updateTerminalEntry(runMeta.entryId, {'), true)
  assert.equal(source.includes("origin: 'user'"), true)
  assert.equal(source.includes("toast.success('Selection Complete'"), false)
  assert.equal(source.includes("toast.success('Execution Complete'"), false)
  assert.equal(source.includes("toast.warning('Execution in progress'"), true)
})
