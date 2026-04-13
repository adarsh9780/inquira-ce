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
  assert.equal(sidebarSource.includes("if (normalized === 'workspace')"), true)
  assert.equal(sidebarSource.includes("if (normalized === 'schema-editor')"), false)

  // Sidebar no longer has workspace/schema specific collapse logic
  // (it still has toggleSidebar for header click, but not for tab switching)
  assert.equal(sidebarSource.includes("if (appStore.activeTab === 'workspace')"), false)
  assert.equal(sidebarSource.includes("if (appStore.activeTab === 'schema-editor')"), false)

  // Workspace/schema toggle is now in status bar
  assert.equal(statusBarSource.includes('switchToWorkspace'), true)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), true)
  assert.equal(statusBarSource.includes("appStore.activeTab === 'workspace'"), true)
  assert.equal(statusBarSource.includes("appStore.activeTab === 'schema-editor'"), true)
})

test('sidebar has settings and terms (CE: no logout)', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')

  // Settings button instead of workspace/schema tabs
  assert.equal(sidebarSource.includes('@click="openSettings'), true)
  assert.equal(sidebarSource.includes('title="Settings"'), true)
  assert.equal(sidebarSource.includes('aria-label="Settings"'), true)

  // Terms button
  assert.equal(sidebarSource.includes('@click="openTerms'), true)
  assert.equal(sidebarSource.includes('title="Terms & Conditions"'), true)
  assert.equal(sidebarSource.includes('aria-label="Terms & Conditions"'), true)

  // CE: Logout removed — no auth needed
  assert.equal(sidebarSource.includes('@click="promptLogout'), false)
  assert.equal(sidebarSource.includes('title="Logout"'), false)
})
