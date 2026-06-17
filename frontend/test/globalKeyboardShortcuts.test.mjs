import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app registers VS Code-like global shortcuts for sidebar, terminal, and workspace layout', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(appSource.includes('function handleGlobalShortcuts(event) {'), true)
  assert.equal(appSource.includes('const hasPrimaryModifier = event.metaKey || event.ctrlKey'), true)
  assert.equal(appSource.includes("import { matchShortcut } from './utils/keyboardShortcuts'"), true)
  assert.equal(appSource.includes('const layoutShortcut = resolveWorkspaceLayoutShortcut(event)'), true)
  assert.equal(appSource.includes('appStore.setWorkspaceLayoutMode(layoutShortcut)'), true)
  assert.equal(appSource.includes("matchShortcut(event, 'conversation-tree')"), true)
  assert.equal(appSource.includes("matchShortcut(event, 'schema')"), true)
  assert.equal(appSource.includes("matchShortcut(event, 'keyboard-shortcuts')"), true)
  assert.equal(appSource.includes("matchShortcut(event, 'dataset-import')"), true)
  assert.equal(appSource.includes("matchShortcut(event, 'sidebar')"), true)
  assert.equal(appSource.includes("matchShortcut(event, 'terminal')"), true)
  assert.equal(appSource.includes("matchShortcut(event, 'layout-cycle')"), true)
  assert.equal(appSource.includes("appStore.setActiveTab('conversation-tree')"), true)
  assert.equal(appSource.includes("appStore.setActiveTab('schema-editor')"), true)
  assert.equal(appSource.includes('appStore.openKeyboardShortcuts()'), true)
  assert.equal(appSource.includes('toggleSidebarVisibility()'), true)
  assert.equal(appSource.includes('appStore.toggleTerminal()'), true)
  assert.equal(appSource.includes('appStore.cycleWorkspaceLayoutMode()'), true)
  assert.equal(appSource.includes('if (!appStore.showSidebar) {'), true)
  assert.equal(appSource.includes('appStore.setWorkspaceLayoutMode(WORKSPACE_LAYOUT_MODES.VIEW)'), true)
  assert.equal(appSource.includes("document.addEventListener('keydown', handleGlobalShortcuts)"), true)
  assert.equal(appSource.includes("document.removeEventListener('keydown', handleGlobalShortcuts)"), true)
})
