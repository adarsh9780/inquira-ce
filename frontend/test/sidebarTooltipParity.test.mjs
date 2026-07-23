import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses native title tooltips for current navigation actions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const rowSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversationRow.vue'), 'utf-8')

  assert.equal(source.includes('title="New conversation"'), true)
  assert.equal(source.includes('Search conversations'), false)
  assert.equal(rowSource.includes('title="Conversation actions"'), true)
  assert.equal(source.includes('title="Data sources"'), true)
  assert.equal(source.includes("shortcutTooltip('schema', 'Schema editor')"), true)
  assert.equal(source.includes("shortcutTooltip('conversation-tree', 'Conversation tree')"), true)
  assert.equal(source.includes('title="Settings"'), true)
  assert.equal(source.includes('title="Profile Settings"'), true)
  assert.equal(source.includes('title="API Keys"'), false)
  assert.equal(source.includes("uiStore.isSidebarCollapsed ? 'Expand sidebar' : 'Inquira'"), true)
  assert.equal(source.includes('title="Collapse sidebar"'), true)
})
