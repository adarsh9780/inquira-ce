import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar communicates workspaces, chats, and restrained utility actions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const menuSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversationActionsMenu.vue'), 'utf-8')

  assert.equal(source.includes('Workspace settings'), true)
  assert.equal(source.includes('workspaceRuntimeLabel'), false)
  assert.equal(source.includes('sidebarConversationsByWorkspace'), true)
  assert.equal(source.includes('visibleConversationsForSidebar(workspace)'), true)
  assert.equal(source.includes('Search conversations'), false)
  assert.equal(source.includes('New analysis'), false)
  assert.equal(source.includes('title="New conversation"'), false)
  assert.equal(source.includes('No conversations yet'), true)
  assert.equal(menuSource.includes('data-conversation-actions-menu'), true)
  assert.equal(source.includes('Workspace tools'), false)
  assert.equal(source.includes('Data sources'), false)
  assert.equal(source.includes('Workspace data'), true)
  assert.equal(source.includes('Conversation tree'), true)
  assert.equal(source.includes('Profile Settings'), true)
  assert.equal(source.includes('Datasets</p>'), false)
  assert.equal(source.includes('ListboxButton'), false)
})

test('global typography still uses shared font tokens', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--font-ui:'), true)
  assert.equal(source.includes('--font-display:'), true)
  assert.equal(source.includes('font-family: var(--font-ui);'), true)
})
