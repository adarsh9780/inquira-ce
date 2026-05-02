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
  assert.equal(source.includes('class="sidebar-rail-label truncate">Create Workspace</span>'), true)
  assert.equal(source.includes('class="sidebar-rail-label truncate">LLM &amp; API Keys</span>'), true)
  assert.equal(source.includes('class="sidebar-rail-label truncate">User Profile</span>'), true)
  assert.equal(source.includes('sidebar-brand-toggle'), true)
  assert.equal(source.includes('sidebar-brand-logo-shell'), true)
  assert.equal(source.includes('sidebar-profile-badge'), true)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('Conversations'), true)
})

test('sidebar profile menu routes terms account and theme through settings modal', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('data-profile-menu'), true)
  assert.equal(source.includes("function openProfileSection(tab) {"), true)
  assert.equal(source.includes('const profileInitials = computed(() => {'), true)
  assert.equal(source.includes('class="layer-modal-dropdown fixed overflow-hidden rounded-xl border shadow-lg"'), true)
  assert.equal(source.includes("@click=\"openProfileSection('terms')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('account')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('appearance')\""), true)
  assert.equal(source.includes('title="Settings"'), false)
})
