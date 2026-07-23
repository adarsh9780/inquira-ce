import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app keeps one sidebar container with a collapsed state only', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('function toggleSidebarVisibility() {'), false)
  assert.equal(appSource.includes('class="h-full shrink-0 app-nav-pane"'), true)
  assert.equal(appSource.includes("'app-nav-pane-collapsed': uiStore.isSidebarCollapsed"), true)
  assert.equal(appSource.includes('app-nav-pane-hidden'), false)
  assert.equal(appSource.includes(':aria-hidden="!appStore.showSidebar"'), false)
  assert.equal(appSource.includes('class="app-sidebar-rail"'), false)
  assert.equal(appSource.includes('@mouseenter='), false)
  assert.equal(appSource.includes('transition: width var(--motion-duration-slow) var(--motion-ease-spring);'), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(appSource.includes('.app-nav-pane-hidden {'), false)
  assert.equal(appSource.includes('<StatusBar />'), true)

  assert.equal(sidebarSource.includes('Workspace settings'), true)
  assert.equal(sidebarSource.includes('function openWorkspaceRail(target = \'\') {'), false)
  assert.equal(sidebarSource.includes('title="Conversations"'), false)
  assert.equal(sidebarSource.includes('title="Settings"'), true)
  assert.equal(sidebarSource.includes('<SidebarConversations'), false)
  assert.equal(sidebarSource.includes('visibleConversationsForSidebar(workspace)'), true)
})
