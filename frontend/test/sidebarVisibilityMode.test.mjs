import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app keeps a single sidebar container and relies on click-only collapse state', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('function toggleSidebarVisibility() {'), true)
  assert.equal(appSource.includes("class=\"h-full shrink-0 app-nav-pane\""), true)
  assert.equal(appSource.includes(":class=\"{ 'app-nav-pane-collapsed': appStore.isSidebarCollapsed }\""), true)
  assert.equal(appSource.includes('class="app-sidebar-rail"'), false)
  assert.equal(appSource.includes('expandSidebarFromRail'), false)
  assert.equal(appSource.includes('@mouseenter='), false)
  assert.equal(appSource.includes('transition: width var(--motion-duration-standard) var(--motion-ease-standard);'), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(appSource.includes('<StatusBar />'), true)

  assert.equal(sidebarSource.includes('class="sidebar-rail-btn"'), true)
  assert.equal(sidebarSource.includes('class="sidebar-rail shrink-0 border-r px-2 py-3"'), true)
  assert.equal(sidebarSource.includes('function openWorkspaceRail(target = \'\') {'), true)
  assert.equal(sidebarSource.includes("title=\"Datasets\""), true)
  assert.equal(sidebarSource.includes("title=\"Conversations\""), true)
  assert.equal(sidebarSource.includes("title=\"LLM & API Keys\""), true)
  assert.equal(sidebarSource.includes(":class=\"appStore.isSidebarCollapsed ? 'sidebar-rail-collapsed' : 'sidebar-rail-expanded'\""), true)
})
