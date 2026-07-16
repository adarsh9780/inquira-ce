import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('unified sidebar routes workspace entry points to settings workspace tab and dataset management stays in workspace settings', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const workspaceTabSource = readFileSync(resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'), 'utf-8')

  assert.equal(source.includes("@click.stop=\"appStore.openSettings('workspace')\""), true)
  assert.equal(source.includes("openSettings('workspace', 1)"), false)
  assert.equal(source.includes('settingsInitialStep'), false)
  assert.equal(workspaceTabSource.includes('data-testid="workspace-import-datasets-dropzone"'), true)
  assert.equal(workspaceTabSource.includes('title="Delete Dataset"'), true)
  assert.equal(source.includes('WorkspaceCreateModal'), false)
})

test('workspace unified editor renders inline dataset actions and remove confirmation UX', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'), 'utf-8')

  assert.equal(source.includes('pendingRemovalDataset'), true)
  assert.equal(source.includes('datasetDeleteDialogMessage'), true)
  assert.equal(source.includes('title="Regenerate schema"'), true)
  assert.equal(source.includes('title="Remove dataset"'), true)
  assert.equal(source.includes('@confirm="confirmRemoveDataset"'), true)
})
