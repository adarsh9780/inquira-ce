import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace and schema navigation live in the sidebar instead of the status bar', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')
  const statusBarSource = readFileSync(statusBarPath, 'utf-8')

  assert.equal(sidebarSource.includes("@click=\"openSettings('workspace', 1)\""), true)
  assert.equal(sidebarSource.includes('@click="openSchemaEditor"'), true)
  assert.equal(sidebarSource.includes('CircleStackIcon'), true)
  assert.equal(sidebarSource.includes('Schema'), true)
  assert.equal(sidebarSource.includes('Inspect datasets and column metadata'), true)
  assert.equal(statusBarSource.includes('switchToWorkspace'), false)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), false)
  assert.equal(statusBarSource.includes('FolderOpenIcon'), false)
  assert.equal(statusBarSource.includes('DocumentTextIcon'), false)
})

test('sidebar uses settings, collapse, and profile actions in the footer', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')

  assert.equal(sidebarSource.includes('@click="openSettings'), true)
  assert.equal(sidebarSource.includes("@click.stop=\"openSettings('workspace', 1)\""), false)
  assert.equal(sidebarSource.includes('title="Settings"'), true)
  assert.equal(sidebarSource.includes('title="Profile Settings"'), true)
  assert.equal(sidebarSource.includes("appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"), true)
  assert.equal(sidebarSource.includes('Legal &amp; Terms'), true)
  assert.equal(sidebarSource.includes('Account Settings'), true)
  assert.equal(sidebarSource.includes('Theme Preference'), true)
  assert.equal(sidebarSource.includes('@click="promptLogout'), false)
})
