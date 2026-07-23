import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace delete uses a shared confirmation modal from the workspace list', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('isWorkspaceDeleteDialogOpen'), true)
  assert.equal(source.includes('workspaceDeleteDialogMessage'), true)
  assert.equal(source.includes('@click.stop="requestDeleteWorkspace(workspace.id)"'), true)
  assert.equal(source.includes('title="Delete workspace"'), true)
  assert.equal(source.includes('aria-label="Delete workspace"'), true)
  assert.equal(source.includes('group-hover:opacity-100'), true)
  assert.equal(source.includes('showDeleteConfirm'), false)
  assert.equal(source.includes('Danger zone'), false)
})
