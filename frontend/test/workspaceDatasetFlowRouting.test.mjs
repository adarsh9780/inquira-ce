import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('unified sidebar routes workspace entry points to settings workspace tab and dataset management stays in workspace settings', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const workspaceTabSource = readFileSync(resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'), 'utf-8')

  assert.equal(source.includes("@click=\"openSettings('workspace', 1)\""), true)
  assert.equal(source.includes(':initial-step="settingsInitialStep"'), true)
  assert.equal(source.includes('const settingsInitialStep = ref(1)'), true)
  assert.equal(source.includes('function openSettings(tab = \'llm\', step = 1) {'), true)
  assert.equal(workspaceTabSource.includes('+ Add dataset'), true)
  assert.equal(workspaceTabSource.includes('title="Delete Dataset"'), true)
  assert.equal(source.includes('WorkspaceCreateModal'), false)
})

test('workspace stepper state-b flow renders inline dataset actions and remove confirmation UX', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/modals/WorkspaceStepper.vue'), 'utf-8')

  assert.equal(source.includes('pendingRemovalTable === dataset.table_name'), true)
  assert.equal(source.includes('Remove {{ formatDatasetName(dataset.table_name) }}?'), true)
  assert.equal(source.includes("@click=\"emit('confirm-remove-dataset', dataset)\""), true)
  assert.equal(source.includes("@click=\"emit('cancel-remove-dataset')\""), true)
  assert.equal(source.includes('title="Refresh from source file"'), true)
  assert.equal(source.includes('title="Remove dataset from workspace"'), true)
})
