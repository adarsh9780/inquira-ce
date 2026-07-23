import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar renders grouped workspaces with lazy conversation caches', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('v-for="workspace in filteredSidebarWorkspaces"'), true)
  assert.equal(source.includes('sidebarConversationsByWorkspace'), true)
  assert.equal(source.includes('loadSidebarConversations'), true)
  assert.equal(source.includes('selectConversation(workspace.id, conv.id)'), true)
  assert.equal(source.includes('normalizedSidebarSearchQuery'), false)
  assert.equal(source.includes('appStore.conversations.length'), false)
})

test('status bar keeps resource recommendations while workspace context moves to the context bar', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')
  const contextBar = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceContextBar.vue'), 'utf-8')

  assert.equal(source.includes('data-workspace-switcher'), false)
  assert.equal(source.includes('workspaceResourceRecommendation'), true)
  assert.equal(source.includes('Workspace cleanup suggested'), true)
  assert.equal(contextBar.includes('data-workspace-context-bar'), true)
  assert.equal(contextBar.includes('data-workspace-status'), true)
  assert.equal(source.includes('Kernel Ready'), false)
  assert.equal(source.includes('Restart Kernel'), false)
})
