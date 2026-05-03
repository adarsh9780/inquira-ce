import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar shows active workspace context with conversations beneath it', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('activeWorkspaceName'), true)
  assert.equal(source.includes('activeWorkspaceCaption'), true)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('Chats'), true)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('SidebarConversations'), false)
})
