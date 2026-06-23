import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar conversation rows use compact timestamps and hover/focus actions', () => {
  const sidebarSource = read('src/components/layout/UnifiedSidebar.vue')
  const rowSource = read('src/components/layout/sidebar/SidebarConversationRow.vue')

  assert.equal(sidebarSource.includes('<SidebarConversationRow'), true)
  assert.equal(sidebarSource.includes(':compact-timestamp="formatConversationTimestamp(conv)"'), true)
  assert.equal(sidebarSource.includes('formatCompactRelativeTimestamp'), true)
  assert.equal(sidebarSource.includes('formatExactTimestamp'), true)
  assert.equal(sidebarSource.includes('absolute right-2 top-1/2 -translate-y-1/2 opacity-0'), false)
  assert.equal(rowSource.includes('sidebar-conversation-time'), true)
  assert.equal(rowSource.includes('group-hover/sidebar-conversation:opacity-0'), true)
  assert.equal(rowSource.includes('group-focus-within/sidebar-conversation:opacity-0'), true)
  assert.equal(rowSource.includes('sidebar-conversation-action'), true)
  assert.equal(rowSource.includes('EllipsisHorizontalIcon'), true)
})

test('sidebar conversation menu shows exact date, divider, rename, and delete', () => {
  const sidebarSource = read('src/components/layout/UnifiedSidebar.vue')
  const menuSource = read('src/components/layout/sidebar/SidebarConversationActionsMenu.vue')

  assert.equal(sidebarSource.includes('<SidebarConversationActionsMenu'), true)
  assert.equal(sidebarSource.includes(':exact-date="activeConversationMenuExactDate"'), true)
  assert.equal(menuSource.includes('{{ exactDate }}'), true)
  assert.equal(menuSource.includes('class="my-1 h-px bg-[var(--color-border)] opacity-70"'), true)
  assert.equal(menuSource.includes('Rename'), true)
  assert.equal(menuSource.includes('Delete'), true)
  assert.equal(menuSource.includes('data-conversation-actions-menu'), true)
})

test('sidebar stale conversation deletion and hidden legal code stay removed', () => {
  const sidebarSource = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(sidebarSource.includes('pendingDeleteIds'), false)
  assert.equal(sidebarSource.includes('pendingDeleteType'), false)
  assert.equal(sidebarSource.includes('v-if="false"'), false)
  assert.equal(sidebarSource.includes('Delete {{ selectedConversationIds.size }}'), false)
})

test('frontend ui audit records token, component, and stale-code findings', () => {
  const auditSource = read('../docs/frontend-ui-audit.md')

  assert.equal(auditSource.includes('text-white'), true)
  assert.equal(auditSource.includes('bg-black/25'), true)
  assert.equal(auditSource.includes('Floating action menus should be shared'), true)
  assert.equal(auditSource.includes('Dropdown internals are duplicated'), true)
  assert.equal(auditSource.includes('isRenamingWorkspace.value = true` twice'), true)
})
