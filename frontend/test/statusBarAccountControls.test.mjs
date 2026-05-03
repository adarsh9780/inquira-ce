import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar keeps workspace/schema controls and no longer renders the local user toggle', () => {
  const statusBarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(statusBarSource.includes('@click.stop="toggleSidebarFromStatusBar"'), false)
  assert.equal(statusBarSource.includes('toggleSidebarFromStatusBar'), false)
  assert.equal(statusBarSource.includes('accountDisplayLabel'), false)
  assert.equal(statusBarSource.includes('ChevronRightIcon'), false)
  assert.equal(statusBarSource.includes('ChevronLeftIcon'), false)
  assert.equal(statusBarSource.includes('switchToWorkspace'), true)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), true)
  assert.equal(statusBarSource.includes('FolderOpenIcon'), true)
  assert.equal(statusBarSource.includes('DocumentTextIcon'), true)
})

test('sidebar owns the profile and bottom action stack', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('title="API Keys"'), true)
  assert.equal(sidebarSource.includes('title="Profile Settings"'), true)
  assert.equal(sidebarSource.includes('Legal &amp; Terms'), true)
  assert.equal(sidebarSource.includes('Account Settings'), true)
  assert.equal(sidebarSource.includes('Theme Preference'), true)
  assert.equal(sidebarSource.includes('Open workspace settings'), true)
  assert.equal(sidebarSource.includes('Chats'), true)
  assert.equal(sidebarSource.includes('Datasets</p>'), false)
  assert.equal(sidebarSource.includes('DocumentTextIcon'), false)
})
