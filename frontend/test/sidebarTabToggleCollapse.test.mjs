import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace/schema toggle is in status bar, not sidebar', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')
  const statusBarSource = readFileSync(statusBarPath, 'utf-8')

  // Sidebar no longer has workspace/schema tab buttons
  assert.equal(sidebarSource.includes("@click=\"handleTabClick('workspace')\""), false)
  assert.equal(sidebarSource.includes("@click=\"handleTabClick('schema-editor')\""), false)
  assert.equal(sidebarSource.includes("if (normalized === 'workspace' || normalized === 'data')"), true)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'schema-editor'"), false)

  // Sidebar no longer has workspace/schema specific collapse logic
  // (it still has toggleSidebar for header click, but not for tab switching)
  assert.equal(sidebarSource.includes('function openWorkspaceRail(target = \'\') {'), false)
  assert.equal(sidebarSource.includes('function openSchemaFromRail() {'), false)

  // Workspace/schema toggle is now in status bar
  assert.equal(statusBarSource.includes('switchToWorkspace'), true)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), true)
  assert.equal(statusBarSource.includes("appStore.activeTab === 'workspace'"), true)
  assert.equal(statusBarSource.includes("appStore.activeTab === 'schema-editor'"), true)
})

test('sidebar replaces direct settings/terms buttons with llm rail and profile menu (CE: no logout)', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')

  // LLM entry button replaces dedicated settings icon
  assert.equal(sidebarSource.includes('@click="openSettings'), true)
  assert.equal(sidebarSource.includes('title="LLM & API Keys"'), true)
  assert.equal(sidebarSource.includes('aria-label="LLM & API Keys"'), true)

  // Profile menu owns terms/account/theme shortcuts
  assert.equal(sidebarSource.includes('title="User Profile"'), true)
  assert.equal(sidebarSource.includes('Terms and Conditions'), true)
  assert.equal(sidebarSource.includes('Account'), true)
  assert.equal(sidebarSource.includes('Theme'), true)
  assert.equal(sidebarSource.includes('Open workspace settings'), true)

  // CE: Logout removed — no auth needed
  assert.equal(sidebarSource.includes('@click="promptLogout'), false)
  assert.equal(sidebarSource.includes('title="Logout"'), false)
})
