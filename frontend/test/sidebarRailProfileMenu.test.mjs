import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar keeps a vertical rail in both modes and shows labels only when expanded', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes("class=\"sidebar-rail shrink-0 border-r px-2 py-3\""), true)
  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'sidebar-rail-collapsed' : 'sidebar-rail-expanded'"), true)
  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'sidebar-rail-btn-collapsed' : 'sidebar-rail-btn-expanded'"), true)
  assert.equal(source.includes('v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">Datasets</span>'), true)
  assert.equal(source.includes('v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">Conversations</span>'), true)
  assert.equal(source.includes('v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">LLM &amp; API Keys</span>'), true)
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
