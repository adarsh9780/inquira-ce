import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar keeps the bottom action stack and expanded-only labels', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes('Settings'), true)
  assert.equal(source.includes("{{ appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar' }}"), false)
  assert.equal(source.includes('class="sidebar-nav-row justify-start px-2.5"'), true)
  assert.equal(source.includes('{{ profileDisplayName }}'), true)
  assert.equal(source.includes('sidebar-initials-avatar'), true)
  assert.equal(source.includes('UserCircleIcon'), false)
  assert.equal(source.includes('Workspace settings'), true)
  assert.equal(source.includes('visibleConversationsForSidebar(workspace)'), true)
  assert.equal(source.includes('Conversation Tree'), true)
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
  assert.equal(source.includes('title="Settings"'), true)
})
