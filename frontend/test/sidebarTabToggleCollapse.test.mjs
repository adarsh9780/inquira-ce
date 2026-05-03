import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace/schema toggle is in status bar, not sidebar', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')
  const statusBarSource = readFileSync(statusBarPath, 'utf-8')

  assert.equal(sidebarSource.includes("@click=\"handleTabClick('workspace')\""), false)
  assert.equal(sidebarSource.includes("@click=\"handleTabClick('schema-editor')\""), false)
  assert.equal(sidebarSource.includes('openSettings(\'workspace\', 1)'), true)
  assert.equal(sidebarSource.includes('function openWorkspaceRail(target = \'\') {'), false)
  assert.equal(sidebarSource.includes('function openSchemaFromRail() {'), false)
  assert.equal(statusBarSource.includes('switchToWorkspace'), true)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), true)
})

test('sidebar uses api/profile actions instead of the old direct settings footer', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')

  assert.equal(sidebarSource.includes('@click="openSettings'), true)
  assert.equal(sidebarSource.includes('title="API Keys"'), true)
  assert.equal(sidebarSource.includes('title="Profile Settings"'), true)
  assert.equal(sidebarSource.includes('Legal &amp; Terms'), true)
  assert.equal(sidebarSource.includes('Account Settings'), true)
  assert.equal(sidebarSource.includes('Theme Preference'), true)
  assert.equal(sidebarSource.includes('@click="promptLogout'), false)
})
