import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar keeps workspace/schema controls and no longer renders the local user toggle', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )

  assert.equal(statusBarSource.includes('@click.stop="toggleSidebarFromStatusBar"'), false)
  assert.equal(statusBarSource.includes('toggleSidebarFromStatusBar'), false)
  assert.equal(statusBarSource.includes('accountDisplayLabel'), false)
  assert.equal(statusBarSource.includes('ChevronRightIcon'), false)
  assert.equal(statusBarSource.includes('ChevronLeftIcon'), false)

  assert.equal(statusBarSource.includes('switchToWorkspace'), true)
  assert.equal(statusBarSource.includes('switchToSchemaEditor'), true)
  assert.equal(statusBarSource.includes('FolderOpenIcon'), true)
  assert.equal(statusBarSource.includes('DocumentTextIcon'), true)
  assert.equal(statusBarSource.includes('Ln {{ appStore.editorLine }}'), true)
  assert.equal(statusBarSource.includes('Col {{ appStore.editorCol }}'), true)
  assert.equal(statusBarSource.includes('Enter data focus mode (Cmd/Ctrl+Shift+D)'), true)
  assert.equal(statusBarSource.includes('Toggle terminal panel (Cmd/Ctrl+J)'), true)
})

test('sidebar owns the profile and bottom action stack', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(sidebarSource.includes('title="Create Workspace"'), true)
  assert.equal(sidebarSource.includes('title="LLM & API Keys"'), true)
  assert.equal(sidebarSource.includes('title="User Profile"'), true)
  assert.equal(sidebarSource.includes('Terms and Conditions'), true)
  assert.equal(sidebarSource.includes('Account'), true)
  assert.equal(sidebarSource.includes('Theme'), true)
  assert.equal(sidebarSource.includes('Workspace'), true)
  assert.equal(sidebarSource.includes('Conversations'), true)
  assert.equal(sidebarSource.includes('Datasets</p>'), false)
  assert.equal(sidebarSource.includes('DocumentTextIcon'), false)
})

test('workspace/schema toggle buttons keep token-based active styling', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )

  assert.ok(statusBarSource.includes("title=\"'Switch to Workspace'\""))
  assert.ok(statusBarSource.includes("title=\"'Switch to Schema Editor'\""))
  assert.ok(statusBarSource.includes("appStore.activeTab === 'workspace'"))
  assert.ok(statusBarSource.includes("appStore.activeTab === 'schema-editor'"))
  assert.ok(statusBarSource.includes("text-[var(--color-accent)] font-medium"))
})
