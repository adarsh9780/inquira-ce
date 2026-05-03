import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar keeps the bottom action stack and expanded-only labels', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3'"), true)
  assert.equal(source.includes('class="text-[13px] font-medium">API Keys</span>'), true)
  assert.equal(source.includes('{{ profileDisplayName }}'), true)
  assert.equal(source.includes('sidebar-initials-avatar'), true)
  assert.equal(source.includes('UserCircleIcon'), false)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('Chats'), true)
})

test('sidebar profile menu routes terms, account, and appearance through settings', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('function openProfileSection(tab) {'), true)
  assert.equal(source.includes('profileInitials'), true)
  assert.equal(source.includes('class="sidebar-profile-menu layer-dropdown fixed w-48 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-lg"'), true)
  assert.equal(source.includes('profileMenuStyle'), true)
  assert.equal(source.includes("@click=\"openProfileSection('terms')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('account')\""), true)
  assert.equal(source.includes("@click=\"openProfileSection('appearance')\""), true)
  assert.equal(source.includes('title="Settings"'), false)
})
