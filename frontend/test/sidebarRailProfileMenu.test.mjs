import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar keeps a fixed bottom action stack and shows labels only when expanded', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'nav-btn-collapsed' : 'nav-btn-expanded'"), true)
  assert.equal(source.includes('class="truncate text-[13px] font-medium">New Workspace</span>'), true)
  assert.equal(source.includes('class="truncate text-[13px] font-medium">API Keys</span>'), true)
  assert.equal(source.includes('class="truncate text-[13px] font-medium">Profile</span>'), true)
  assert.equal(source.includes('brand-btn h-full w-full px-3'), true)
  assert.equal(source.includes('sidebar-brand-wordmark'), true)
  assert.equal(source.includes('UserCircleIcon'), true)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('Chats'), true)
})

test('sidebar profile menu routes terms account and theme through settings modal', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('data-profile-menu'), true)
  assert.equal(source.includes("function openProfileSection(tab) {"), true)
  assert.equal(source.includes('UserCircleIcon'), true)
  assert.equal(source.includes('class="profile-menu absolute bottom-0 left-full z-[var(--z-dropdown)] ml-2 w-48 overflow-hidden rounded-xl border shadow-lg"'), true)
  assert.equal(source.includes("@click=\"openProfileSection('terms')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('account')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('appearance')\""), true)
  assert.equal(source.includes('title="Settings"'), false)
})
