import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar lists workspace conversations while the context bar owns active context', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const contextSource = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceContextBar.vue'), 'utf-8')
  const menuSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversationActionsMenu.vue'), 'utf-8')

  assert.equal(source.includes('workspaceRuntimeLabel'), false)
  assert.equal(source.includes('sidebarConversationsByWorkspace'), true)
  assert.equal(source.includes("@click.stop=\"uiStore.openSettings('workspace')\""), true)
  assert.equal(source.includes('openSchemaEditor'), true)
  assert.equal(source.includes('CircleStackIcon'), true)
  assert.equal(source.includes('visibleConversationsForSidebar(workspace)'), true)
  assert.equal(source.includes('filteredSidebarWorkspaces'), true)
  assert.equal(menuSource.includes('data-conversation-actions-menu'), true)
  assert.equal(source.includes('SidebarDatasets'), false)
  assert.equal(source.includes('Workspace tools'), false)
  assert.equal(source.includes('Data sources'), true)
  assert.equal(source.includes('Conversation tree'), true)
  assert.equal(contextSource.includes('data-workspace-context-bar'), true)
  assert.equal(contextSource.includes('{{ activeWorkspaceName }}'), true)
  assert.equal(contextSource.includes('data-action="add-data"'), true)
  assert.equal(contextSource.includes('workspaceActivation.openDataConnectionFlow()'), true)
})
