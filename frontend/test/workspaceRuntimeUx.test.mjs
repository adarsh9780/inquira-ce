import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar renders grouped workspaces with lazy conversation caches', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('v-for="workspace in appStore.workspaces"'), true)
  assert.equal(source.includes('sidebarConversationsByWorkspace'), true)
  assert.equal(source.includes('loadSidebarConversations'), true)
  assert.equal(source.includes('selectConversation(workspace.id, conv.id)'), true)
  assert.equal(source.includes('appStore.conversations.length'), false)
})

test('status bar exposes workspace switcher and resource recommendations without kernel copy', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('data-workspace-switcher'), true)
  assert.equal(source.includes('workspaceResourceRecommendation'), true)
  assert.equal(source.includes('Workspace cleanup suggested'), true)
  assert.equal(source.includes('Kernel Ready'), false)
  assert.equal(source.includes('Restart Kernel'), false)
})
