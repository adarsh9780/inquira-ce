import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses file explorer layout without arrow toggle', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  assert.equal(source.includes('function toggleSidebar() {'), true)
  assert.equal(source.includes('@click="toggleSidebar"'), true)
  assert.equal(source.includes('Expand sidebar'), false)
  assert.equal(source.includes('Collapse sidebar'), false)
  assert.equal(source.includes('SidebarWorkspaces'), true)
  assert.equal(source.includes('SidebarDatasets'), true)
  assert.equal(source.includes('SidebarConversations'), true)
  assert.equal(source.includes('Kernel'), false)
})
