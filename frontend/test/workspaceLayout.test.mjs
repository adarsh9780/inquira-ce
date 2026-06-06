import test from 'node:test'
import assert from 'node:assert/strict'
import {
  nextWorkspaceLayoutMode,
  normalizeWorkspaceLayoutMode,
  resolveWorkspaceLayoutShortcut,
  workspaceLayoutVisibility,
} from '../src/utils/workspaceLayout.js'

test('workspace layout normalizes current, legacy, missing, and invalid modes', () => {
  assert.equal(normalizeWorkspaceLayoutMode('view'), 'view')
  assert.equal(normalizeWorkspaceLayoutMode('chat'), 'chat')
  assert.equal(normalizeWorkspaceLayoutMode('output'), 'output')
  assert.equal(normalizeWorkspaceLayoutMode('split'), 'view')
  assert.equal(normalizeWorkspaceLayoutMode('data'), 'output')
  assert.equal(normalizeWorkspaceLayoutMode('invalid'), 'view')
  assert.equal(normalizeWorkspaceLayoutMode(), 'view')
})

test('workspace layout cycles View to Chat to Output', () => {
  assert.equal(nextWorkspaceLayoutMode('view'), 'chat')
  assert.equal(nextWorkspaceLayoutMode('chat'), 'output')
  assert.equal(nextWorkspaceLayoutMode('output'), 'view')
})

test('workspace layout visibility matches canonical presets', () => {
  assert.deepEqual(workspaceLayoutVisibility('view'), {
    showSidebar: true,
    showLeftPane: true,
    showRightPane: true,
  })
  assert.deepEqual(workspaceLayoutVisibility('chat'), {
    showSidebar: false,
    showLeftPane: true,
    showRightPane: false,
  })
  assert.deepEqual(workspaceLayoutVisibility('output'), {
    showSidebar: false,
    showLeftPane: false,
    showRightPane: true,
  })
})

test('workspace layout resolves primary Alt shortcuts using event.code', () => {
  assert.equal(resolveWorkspaceLayoutShortcut({ metaKey: true, altKey: true, code: 'KeyV' }), 'view')
  assert.equal(resolveWorkspaceLayoutShortcut({ ctrlKey: true, altKey: true, code: 'KeyC' }), 'chat')
  assert.equal(resolveWorkspaceLayoutShortcut({ ctrlKey: true, altKey: true, code: 'KeyO' }), 'output')
  assert.equal(resolveWorkspaceLayoutShortcut({ ctrlKey: true, code: 'KeyV' }), '')
  assert.equal(resolveWorkspaceLayoutShortcut({ ctrlKey: true, altKey: true, shiftKey: true, code: 'KeyV' }), '')
})
