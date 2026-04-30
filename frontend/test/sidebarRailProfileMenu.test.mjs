import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar keeps a fixed bottom action stack and shows labels only when expanded', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'sidebar-rail-btn-collapsed' : 'sidebar-rail-btn-expanded'"), true)
  assert.equal(source.includes('v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">Create Workspace</span>'), true)
  assert.equal(source.includes('v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">LLM &amp; API Keys</span>'), true)
  assert.equal(source.includes('v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">User Profile</span>'), true)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('Conversations'), true)
})

test('sidebar profile menu routes terms account and theme through settings modal', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('data-profile-menu'), true)
  assert.equal(source.includes("function openProfileSection(tab) {"), true)
  assert.equal(source.includes("@click=\"openProfileSection('terms')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('account')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('appearance')\""), true)
  assert.equal(source.includes('title="Settings"'), false)
})
