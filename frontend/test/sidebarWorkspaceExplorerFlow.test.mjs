import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar shows active workspace context with conversations beneath it', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('activeWorkspaceName'), true)
  assert.equal(source.includes('activeWorkspaceCaption'), true)
  assert.equal(source.includes("@click=\"appStore.openSettings('workspace')\""), true)
  assert.equal(source.includes('openSchemaEditor'), true)
  assert.equal(source.includes('CircleStackIcon'), true)
  assert.equal(source.includes('conversationBadgeLabel(index, appStore.conversations.length)'), true)
  assert.equal(source.includes('data-conversation-actions-menu'), true)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('Conversation Tree'), true)
})
