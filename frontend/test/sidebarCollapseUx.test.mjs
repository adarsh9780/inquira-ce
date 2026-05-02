import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses file explorer layout with unified design', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  // Dedicated top toggle controls the sidebar, with no hover-open behavior
  assert.equal(source.includes('function handleBrandClick() {'), true)
  assert.equal(source.includes('@click="handleBrandClick"'), true)
  assert.equal(source.includes('@mouseenter='), false)
  assert.equal(source.includes('appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)'), true)
  assert.equal(source.includes('sidebar-brand-toggle'), true)
  assert.equal(source.includes('sidebar-brand-logo-shell'), true)
  assert.equal(source.includes('Inquira Asset'), false)
  assert.equal(source.includes('Analysis console'), false)
  assert.equal(source.includes('sidebar-brand-copy'), false)

  // Fixed bottom action stack handles navigation in both sidebar states
  assert.equal(source.includes('class="sidebar-rail-btn"'), true)
  assert.equal(source.includes('function openWorkspaceRail(target = \'\') {'), false)
  assert.equal(source.includes('Expand sidebar'), true)
  assert.equal(source.includes('Collapse sidebar'), true)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('No conversations yet.'), true)

  // No old separate sidebar components - unified design
  assert.equal(source.includes('SidebarWorkspaces'), false)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('SidebarConversations'), false)
  
  // No old collapsed state pattern
  assert.equal(source.includes(':is-collapsed="false"'), false)
  assert.equal(source.includes('v-show="!appStore.isSidebarCollapsed"'), true)
  
  // No Kernel references in sidebar
  assert.equal(source.includes('Kernel'), false)
})
