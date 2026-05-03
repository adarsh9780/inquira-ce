import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses the unified compact workspace/chat layout', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('function handleBrandClick() {'), true)
  assert.equal(source.includes('@click="handleBrandClick"'), true)
  assert.equal(source.includes('@mouseenter='), false)
  assert.equal(source.includes('appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)'), true)
  assert.equal(source.includes('Expand sidebar'), true)
  assert.equal(source.includes('Collapse sidebar'), true)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('Create a workspace to start.'), true)
  assert.equal(source.includes('SidebarWorkspaces'), false)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('SidebarConversations'), false)
  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0'"), true)
  assert.equal(source.includes('Kernel'), false)
})
