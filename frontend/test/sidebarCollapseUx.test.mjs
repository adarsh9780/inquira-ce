import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses file explorer layout with unified design', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  // Toggle sidebar function exists
  assert.equal(source.includes('function toggleSidebar() {'), true)
  assert.equal(source.includes('@click="toggleSidebar"'), true)
  
  // No expand/collapse text labels
  assert.equal(source.includes('Expand sidebar'), false)
  assert.equal(source.includes('Collapse sidebar'), false)
  
  // No old separate sidebar components - unified design
  assert.equal(source.includes('SidebarWorkspaces'), false)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('SidebarConversations'), false)
  
  // No old collapsed state pattern
  assert.equal(source.includes(':is-collapsed="false"'), false)
  assert.equal(source.includes('v-else-if="!appStore.isSidebarCollapsed"'), false)
  
  // No Kernel references in sidebar
  assert.equal(source.includes('Kernel'), false)
})
