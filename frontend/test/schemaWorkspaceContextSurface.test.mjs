import test from 'node:test'
import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { readFileSync } from './sourceText.mjs'

const editor = readFileSync(resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue'), 'utf-8')
const surface = readFileSync(resolve(process.cwd(), 'src/components/schema/WorkspaceContextSurface.vue'), 'utf-8')

test('schema editor delegates workspace context editing to its focused surface', () => {
  assert.equal(editor.includes("import WorkspaceContextSurface from '../schema/WorkspaceContextSurface.vue'"), true)
  assert.equal(editor.includes('v-model="schemaContext"'), true)
  assert.equal(editor.includes(':save-context="saveWorkspaceContext"'), true)
  assert.equal(surface.includes("emit('update:modelValue', context)"), true)
  assert.equal(surface.includes('role="alert"'), true)
})
