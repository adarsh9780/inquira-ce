import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists and exposes three-state workspace layout mode', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes("const workspaceLayoutMode = ref('chat')"), true)
  assert.equal(source.includes("workspace_layout_mode: workspaceLayoutMode.value || 'chat'"), true)
  assert.equal(source.includes("data_focus_mode: workspaceLayoutMode.value === 'data'"), true)
  assert.equal(source.includes('const showLeftPane = computed(() => workspaceLayoutMode.value !== \'data\')'), true)
  assert.equal(source.includes('const showRightPane = computed(() => workspaceLayoutMode.value !== \'chat\')'), true)
  assert.equal(source.includes("if (typeof ui.data_focus_mode === 'boolean')"), true)
  assert.equal(source.includes('function setWorkspaceLayoutMode(mode) {'), true)
  assert.equal(source.includes('function cycleWorkspaceLayoutMode() {'), true)
  assert.equal(source.includes('function setDataFocusMode(enabled) {'), true)
})
