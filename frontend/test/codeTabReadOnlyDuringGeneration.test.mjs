import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab keeps editor visible and switches it to read-only while generation is in progress', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('class="pointer-events-none absolute right-3 top-3 z-10"'), true)
  assert.equal(source.includes('AI is creating Python code for your analysis'), false)
  assert.equal(source.includes('const editableCompartment = new Compartment()'), true)
  assert.equal(source.includes('editableCompartment.of(EditorView.editable.of(!isGeneratingCode.value))'), true)
  assert.equal(source.includes('function syncEditorEditability() {'), true)
  assert.equal(source.includes('editableCompartment.reconfigure(EditorView.editable.of(!isGeneratingCode.value))'), true)
  assert.equal(source.includes('watch(() => appStore.isLoading, (loading) => {'), true)
  assert.equal(source.includes('syncEditorEditability()'), true)
})
