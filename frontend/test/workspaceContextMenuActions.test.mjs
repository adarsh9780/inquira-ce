import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace switcher exposes right-click context actions for rename/delete/clear database', () => {
  const componentPath = resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('@contextmenu.prevent'), true)
  assert.equal(source.includes('Rename Workspace'), true)
  assert.equal(source.includes('Clear Workspace Database'), true)
  assert.equal(source.includes('Delete Workspace'), true)
  assert.equal(source.includes('WorkspaceRenameModal'), true)
})
