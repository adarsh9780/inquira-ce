import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists and exposes canonical three-state workspace layout presets', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('const workspaceLayoutMode = ref(WORKSPACE_LAYOUT_MODES.VIEW)'), true)
  assert.equal(source.includes('workspace_layout_mode: normalizeWorkspaceLayoutMode(workspaceLayoutMode.value)'), true)
  assert.equal(source.includes('const showSidebar = computed(() => layoutVisibility.value.showSidebar)'), true)
  assert.equal(source.includes('const showLeftPane = computed(() => layoutVisibility.value.showLeftPane)'), true)
  assert.equal(source.includes('const showRightPane = computed(() => layoutVisibility.value.showRightPane)'), true)
  assert.equal(source.includes('workspaceLayoutMode.value = normalizeWorkspaceLayoutMode(ui.workspace_layout_mode)'), true)
  assert.equal(source.includes("if (typeof ui.data_focus_mode === 'boolean')"), false)
  assert.equal(source.includes('function setWorkspaceLayoutMode(mode) {'), true)
  assert.equal(source.includes('function cycleWorkspaceLayoutMode() {'), true)
  assert.equal(source.includes('function setDataFocusMode(enabled) {'), true)
  assert.equal(source.includes('setWorkspaceLayoutMode(WORKSPACE_LAYOUT_MODES.VIEW)'), true)
})
