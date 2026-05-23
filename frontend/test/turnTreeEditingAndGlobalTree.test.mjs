import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const chatInputSource = readFileSync(new URL('../src/components/chat/ChatInput.vue', import.meta.url), 'utf8')
const modalSource = readFileSync(new URL('../src/components/chat/TurnTreeModal.vue', import.meta.url), 'utf8')
const sidebarSource = readFileSync(new URL('../src/components/layout/UnifiedSidebar.vue', import.meta.url), 'utf8')
const rightPanelSource = readFileSync(new URL('../src/components/layout/RightPanel.vue', import.meta.url), 'utf8')
const globalTreeSource = readFileSync(new URL('../src/components/layout/sidebar/SidebarGlobalTurnTree.vue', import.meta.url), 'utf8')
const apiServiceSource = readFileSync(new URL('../src/services/apiService.js', import.meta.url), 'utf8')
const storeSource = readFileSync(new URL('../src/stores/appStore.js', import.meta.url), 'utf8')

test('turn tree composer uses a tree-like icon instead of share icon', () => {
  assert.equal(chatInputSource.includes('ShareIcon'), false)
  assert.equal(chatInputSource.includes('QueueListIcon'), true)
})

test('turn tree modal exposes safe edit actions and emits backend-backed operations', () => {
  assert.equal(modalSource.includes("handleContextAction('delete')"), true)
  assert.equal(modalSource.includes("handleContextAction('move-to')"), true)
  assert.equal(modalSource.includes("handleContextAction('move-up')"), true)
  assert.equal(modalSource.includes("handleContextAction('move-down')"), true)
  assert.equal(modalSource.includes('selectedDeleteBlockReason'), true)
  assert.equal(modalSource.includes("'delete-turn'"), true)
  assert.equal(modalSource.includes("'move-turn'"), true)
  assert.equal(modalSource.includes("'reorder-turns'"), true)
})

test('frontend API and store expose turn edit and workspace tree calls', () => {
  assert.equal(apiServiceSource.includes('async v1GetWorkspaceTurnTree(workspaceId)'), true)
  assert.equal(apiServiceSource.includes('async v1DeleteTurn(conversationId, turnId)'), true)
  assert.equal(apiServiceSource.includes('async v1MoveTurn(conversationId, turnId, parentTurnId)'), true)
  assert.equal(apiServiceSource.includes('async v1ReorderTurns(conversationId, parentTurnId, turnIds)'), true)
  assert.equal(storeSource.includes('async function loadWorkspaceTurnTree'), true)
  assert.equal(storeSource.includes('async function deleteTurn(turnId)'), true)
  assert.equal(storeSource.includes('async function moveTurn(turnId, parentTurnId)'), true)
  assert.equal(storeSource.includes('async function reorderTurnSiblings(parentTurnId, turnIds)'), true)
})

test('global tree is routed as a full conversation tree view and opens turns', () => {
  assert.equal(sidebarSource.includes('openConversationTree'), true)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'conversation-tree'"), true)
  assert.equal(sidebarSource.includes('SidebarGlobalTurnTree'), false)
  assert.equal(rightPanelSource.includes("appStore.activeTab === 'conversation-tree'"), true)
  assert.equal(rightPanelSource.includes('<SidebarGlobalTurnTree variant="page" />'), true)
  assert.equal(globalTreeSource.includes('appStore.loadWorkspaceTurnTree()'), true)
  assert.equal(globalTreeSource.includes("appStore.setActiveTab('workspace')"), true)
  assert.equal(globalTreeSource.includes('appStore.loadActiveTurnRelations(targetTurnId)'), true)
})
