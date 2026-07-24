import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store no longer persists alternate workspace layout modes', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appCoordinatorStore.js'), 'utf-8')

  assert.equal(source.includes('workspaceLayoutMode'), false)
  assert.equal(source.includes('workspace_layout_mode'), false)
  assert.equal(source.includes('showSidebar'), false)
  assert.equal(source.includes('showLeftPane'), false)
  assert.equal(source.includes('showRightPane'), false)
  assert.equal(source.includes('setWorkspaceLayoutMode'), false)
  assert.equal(source.includes('cycleWorkspaceLayoutMode'), false)
  assert.equal(source.includes('setDataFocusMode'), false)
  assert.equal(source.includes("if (typeof ui.data_focus_mode === 'boolean')"), false)
})
