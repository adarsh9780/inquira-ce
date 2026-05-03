import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app registers VS Code-like global shortcuts for sidebar, terminal, and workspace layout', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(appSource.includes('function handleGlobalShortcuts(event) {'), true)
  assert.equal(appSource.includes('const hasPrimaryModifier = event.metaKey || event.ctrlKey'), true)
  assert.equal(appSource.includes("if (key === 'b')"), true)
  assert.equal(appSource.includes("if (key === 'j')"), true)
  assert.equal(appSource.includes("if (key === 'd' && event.shiftKey)"), true)
  assert.equal(appSource.includes('toggleSidebarVisibility()'), true)
  assert.equal(appSource.includes('appStore.toggleTerminal()'), true)
  assert.equal(appSource.includes('appStore.cycleWorkspaceLayoutMode()'), true)
  assert.equal(appSource.includes("document.addEventListener('keydown', handleGlobalShortcuts)"), true)
  assert.equal(appSource.includes("document.removeEventListener('keydown', handleGlobalShortcuts)"), true)
})
