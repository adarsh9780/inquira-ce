import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar exposes accessible fixed layout presets', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('aria-label="Workspace layout presets"'), true)
  assert.equal(source.includes('@click="setLayoutPreset(\'view\')"'), true)
  assert.equal(source.includes('@click="setLayoutPreset(\'chat\')"'), true)
  assert.equal(source.includes('@click="setLayoutPreset(\'code\')"'), true)
  assert.equal(source.includes('@click="setLayoutPreset(\'output\')"'), true)
  assert.equal(source.includes("appStore.setWorkspacePane('code')"), true)
  assert.equal(source.includes("appStore.setWorkspacePane('chat')"), true)
  assert.equal(source.includes("if (appStore.workspaceLayoutMode === WORKSPACE_LAYOUT_MODES.CHAT)"), true)
  assert.equal(source.includes("if (appStore.workspaceLayoutMode === WORKSPACE_LAYOUT_MODES.OUTPUT) return 'Data'"), true)
  assert.equal(source.includes("return 'View'"), true)
  assert.equal(source.includes(':aria-keyshortcuts="workspaceLayoutAriaShortcut"'), true)
  assert.equal(source.includes('aria-live="polite"'), true)
})
