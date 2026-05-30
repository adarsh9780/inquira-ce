import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar stays focused on runtime status and no longer renders workspace schema toggles', () => {
  const statusBarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(statusBarSource.includes('@click.stop="toggleSidebarFromStatusBar"'), false)
  assert.equal(statusBarSource.includes('toggleSidebarFromStatusBar'), false)
  assert.equal(statusBarSource.includes('accountDisplayLabel'), false)
  assert.equal(statusBarSource.includes('ChevronRightIcon'), false)
  assert.equal(statusBarSource.includes('ChevronLeftIcon'), false)
  assert.equal(statusBarSource.includes('switchToWorkspace'), false)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), false)
  assert.equal(statusBarSource.includes('FolderOpenIcon'), false)
  assert.equal(statusBarSource.includes('DocumentTextIcon'), false)
  assert.equal(statusBarSource.includes('tokenUsageSummaryLabel'), true)
  assert.equal(statusBarSource.includes('kernelStatusMeta'), true)
})

test('sidebar owns the profile and bottom action stack', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('title="Settings"'), true)
  assert.equal(sidebarSource.includes('title="Profile Settings"'), true)
  assert.equal(sidebarSource.includes("appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"), true)
  assert.equal(sidebarSource.includes('Legal &amp; Terms'), true)
  assert.equal(sidebarSource.includes('Account Settings'), true)
  assert.equal(sidebarSource.includes('Theme Preference'), true)
  assert.equal(sidebarSource.includes("@click=\"openSettings('workspace', 1)\""), true)
  assert.equal(sidebarSource.includes('SidebarConversations'), true)
  assert.equal(sidebarSource.includes('Conversation Tree'), true)
  assert.equal(sidebarSource.includes('Datasets</p>'), false)
  assert.equal(sidebarSource.includes('CircleStackIcon'), true)
})
