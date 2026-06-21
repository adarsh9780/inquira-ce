import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar shows active workspace context with conversations beneath it', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('workspaceRuntimeLabel'), false)
  assert.equal(source.includes('sidebarConversationsByWorkspace'), true)
  assert.equal(source.includes("@click.stop=\"appStore.openSettings('workspace')\""), true)
  assert.equal(source.includes('openSchemaEditor'), true)
  assert.equal(source.includes('CircleStackIcon'), true)
  assert.equal(source.includes('visibleConversationsForWorkspace(workspace.id)'), true)
  assert.equal(source.includes('data-conversation-actions-menu'), true)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('Conversation Tree'), true)
})
