import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf-8')

test('shared dropdown uses one portal positioning system above modal content', () => {
  const dropdown = read('src/components/ui/HeaderDropdown.vue')
  const shared = read('src/components/ui/dropdownShared.ts')
  const dialog = read('src/components/ui/dialog/DialogShell.vue')
  const alertDialog = read('src/components/ui/alert-dialog/AlertDialogShell.vue')

  assert.equal(dropdown.includes('updateFloatingDropdownPosition'), false)
  assert.equal(dropdown.includes('position="popper"'), true)
  assert.equal(dropdown.includes(':side-offset="6"'), true)
  assert.equal(dropdown.includes('align="start"'), true)
  assert.equal(dropdown.includes('position-strategy="fixed"'), true)
  assert.equal(dropdown.includes("width: 'var(--reka-combobox-trigger-width)'"), true)
  assert.equal(shared.includes('layer-modal-dropdown fixed'), false)
  assert.equal(dialog.includes('z-[91]'), false)
  assert.equal(alertDialog.includes('z-[91]'), false)
})

test('runtime source uses the shared styled dropdown instead of a native select', () => {
  const workspaceSettings = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(workspaceSettings.includes('<HeaderDropdown'), true)
  assert.equal(workspaceSettings.includes('v-model="runtimeConfig.mode"'), true)
  assert.equal(workspaceSettings.includes(':options="runtimeSourceOptions"'), true)
  assert.equal(workspaceSettings.includes('<select v-model="runtimeConfig.mode"'), false)
})
