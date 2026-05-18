import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readWorkspaceTab() {
  return readFileSync(
    resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'),
    'utf-8',
  )
}

test('workspace setup uses only context and datasets steps', () => {
  const source = readWorkspaceTab()

  assert.equal(source.includes("{ id: 1, label: 'Workspace context' }"), true)
  assert.equal(source.includes("{ id: 2, label: 'Datasets' }"), true)
  assert.equal(source.includes("{ id: 3, label: 'Generate schema' }"), false)
  assert.equal(source.includes('<!-- Step 3: Generate schema -->'), false)
  assert.equal(source.includes('setupStep.value = 3'), false)
})

test('workspace dataset view is the only schema management surface', () => {
  const source = readWorkspaceTab()

  assert.equal(source.includes('Retry schema generation'), false)
  assert.equal(source.includes('Add at least one dataset before generating schemas.'), false)
  assert.equal(source.includes('@click="generateWorkspaceSchemas"'), false)
  assert.equal(source.includes('Schema generation starts automatically after import.'), false)
})

test('workspace dataset import action is labeled as a primary import datasets action', () => {
  const source = readWorkspaceTab()

  assert.equal(source.includes('>Import datasets</span>'), true)
  assert.equal(source.includes('+ Add datasets'), false)
})
