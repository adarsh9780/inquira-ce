import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar exposes layout presets through one View drop-up', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('data-status-view-menu'), true)
  assert.equal(source.includes('aria-label="View"'), true)
  assert.equal(source.includes('aria-haspopup="menu"'), true)
  assert.equal(source.includes('role="menuitemradio"'), true)
  assert.equal(source.includes('const layoutPresetOptions = ['), true)
  for (const id of ["id: 'view'", "id: 'chat'", "id: 'code'", "id: 'output'"]) {
    assert.equal(source.includes(id), true)
  }
  assert.equal(source.includes('@click="selectLayoutPreset(option.id)"'), true)
  assert.equal(source.includes("appStore.setWorkspacePane('code')"), true)
  assert.equal(source.includes("appStore.setWorkspacePane('chat')"), true)
  assert.equal(source.includes("if (appStore.workspaceLayoutMode === WORKSPACE_LAYOUT_MODES.CHAT)"), true)
  assert.equal(source.includes("if (appStore.workspaceLayoutMode === WORKSPACE_LAYOUT_MODES.OUTPUT) return 'Data'"), true)
  assert.equal(source.includes("return 'View'"), true)
  assert.equal(source.includes(':aria-keyshortcuts="workspaceLayoutAriaShortcut"'), true)
  assert.equal(source.includes('aria-live="polite"'), true)
  assert.equal(source.includes('class="status-layout-preset"'), false)
})
