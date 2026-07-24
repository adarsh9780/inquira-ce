import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app registers global shortcuts for command palette, sidebar, settings, and terminal', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const coordinatorSource = readFileSync(resolve(process.cwd(), 'src/composables/useGlobalShortcuts.ts'), 'utf-8')
  const datasetDropSource = readFileSync(resolve(process.cwd(), 'src/composables/useNativeDatasetDrop.ts'), 'utf-8')
  const interactionSource = [appSource, coordinatorSource, datasetDropSource].join('\n')
  const shortcutsSource = readFileSync(resolve(process.cwd(), 'src/utils/keyboardShortcuts.js'), 'utf-8')

  assert.equal(coordinatorSource.includes('function handleGlobalShortcuts(event: KeyboardEvent) {'), true)
  assert.equal(coordinatorSource.includes('event.metaKey || event.ctrlKey'), true)
  assert.equal(coordinatorSource.includes("import { matchShortcut } from '../utils/keyboardShortcuts'"), true)
  assert.equal(appSource.includes('resolveWorkspaceLayoutShortcut'), false)
  assert.equal(appSource.includes('appStore.setWorkspaceLayoutMode'), false)
  for (const shortcut of ['conversation-tree', 'schema', 'settings', 'sidebar', 'dataset-import', 'command-palette', 'terminal']) {
    assert.equal(coordinatorSource.includes(`'${shortcut}'`), true)
  }
  assert.equal(coordinatorSource.includes("'keyboard-shortcuts'"), false)
  assert.equal(coordinatorSource.includes("'layout-cycle'"), false)
  assert.equal(coordinatorSource.includes("ui.setActiveTab('conversation-tree')"), true)
  assert.equal(coordinatorSource.includes("ui.setActiveTab('schema-editor')"), true)
  assert.equal(coordinatorSource.includes("ui.openSettings('setup')"), true)
  assert.equal(coordinatorSource.includes('ui.setSidebarCollapsed(!ui.isSidebarCollapsed)'), true)
  assert.equal(appSource.includes('uiStore.openKeyboardShortcuts()'), false)
  assert.equal(appSource.includes('<KeyboardShortcutsModal'), true)
  assert.equal(coordinatorSource.includes('ui.toggleCommandPalette()'), true)
  assert.equal(appSource.includes('CommandPaletteModal'), true)
  assert.equal(coordinatorSource.includes('ui.toggleTerminal()'), true)
  assert.equal(datasetDropSource.includes("window.addEventListener('inquira:open-dataset-picker', openDatasetPicker)"), true)
  assert.equal(shortcutsSource.includes("{ id: 'command-palette', category: 'Workspace', label: 'Open Command Palette', keys: ['mod', 'k']"), true)
  assert.equal(shortcutsSource.includes("{ id: 'sidebar', category: 'Workspace', label: 'Toggle Sidebar', keys: ['mod', 'b']"), true)
  assert.equal(shortcutsSource.includes("{ id: 'settings', category: 'Navigation', label: 'Open Settings', keys: ['mod', ',']"), true)
  assert.equal(shortcutsSource.includes("id: 'keyboard-shortcuts'"), false)
  assert.equal(appSource.includes('appStore.cycleWorkspaceLayoutMode()'), false)
  assert.equal(interactionSource.includes("document.addEventListener('keydown', handleGlobalShortcuts)"), true)
  assert.equal(interactionSource.includes("document.removeEventListener('keydown', handleGlobalShortcuts)"), true)
})
