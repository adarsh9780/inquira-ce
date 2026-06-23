import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('conversation delete flow in store re-syncs active conversation and hydrates fallback turns', () => {
  const source = readSource('src/stores/appStore.js')

  assert.equal(source.includes('async function deleteConversationById(conversationId) {'), true)
  assert.equal(source.includes('await apiService.v1DeleteConversation(targetId)'), true)
  assert.equal(source.includes('function clearConversationScopedState(options = {})'), true)
  assert.equal(source.includes("pythonFileContent.value = ''"), true)
  assert.equal(source.includes('activeTurnArtifacts.value = []'), true)
  assert.equal(source.includes('setSelectedTableArtifact(activeWorkspaceId.value, \'\')'), true)
  assert.equal(source.includes('setSelectedFigureArtifact(activeWorkspaceId.value, \'\')'), true)
  assert.equal(source.includes('const activeStillExists = currentActiveId'), true)
  assert.equal(source.includes('await loadWorkspaceTurnTree()'), true)
  assert.equal(source.includes('await fetchConversationTurns({ reset: true })'), true)
  assert.equal(source.includes('setActiveConversationId(fallbackConversationId)'), true)
  assert.equal(source.includes('clearConversationScopedState()'), true)
})

test('sidebar uses a simple conversation list and keeps the tree in the dedicated page', () => {
  const sidebarSource = readSource('src/components/layout/UnifiedSidebar.vue')
  const rowSource = readSource('src/components/layout/sidebar/SidebarConversationRow.vue')
  const menuSource = readSource('src/components/layout/sidebar/SidebarConversationActionsMenu.vue')
  const chatTabSource = readSource('src/components/chat/ChatTab.vue')
  const globalTreeSource = readSource('src/components/layout/sidebar/SidebarGlobalTurnTree.vue')
  const rightPanelSource = readSource('src/components/layout/RightPanel.vue')

  assert.equal(sidebarSource.includes('<SidebarConversations'), false)
  assert.equal(sidebarSource.includes('<SidebarGlobalTurnTree v-else />'), false)
  assert.equal(rightPanelSource.includes('<SidebarGlobalTurnTree variant="page" />'), true)
  assert.equal(sidebarSource.includes('<SidebarConversationRow'), true)
  assert.equal(sidebarSource.includes('<SidebarConversationActionsMenu'), true)
  assert.equal(rowSource.includes("emit('toggle-menu', $event)"), true)
  assert.equal(menuSource.includes('data-conversation-actions-menu'), true)
  assert.equal(sidebarSource.includes('await appStore.deleteConversationById(pendingDeleteId.value)'), true)
  assert.equal(globalTreeSource.includes('appStore.deleteTurn(payload?.turnId, payload?.conversationId)'), true)
  assert.equal(globalTreeSource.includes('ConfirmationModal'), true)
  assert.equal(globalTreeSource.includes('window.confirm'), false)
  assert.equal(sidebarSource.includes('await apiService.v1DeleteConversation(pendingDeleteId.value)'), false)
  assert.equal(chatTabSource.includes('title="Delete Conversation"'), false)
})

test('sidebar no longer exposes flat multi-select conversation deletion', () => {
  const sidebarSource = readSource('src/components/layout/UnifiedSidebar.vue')
  const rowSource = readSource('src/components/layout/sidebar/SidebarConversationRow.vue')

  assert.equal(sidebarSource.includes('@click="handleConversationClick($event, conv.id, index)"'), false)
  assert.equal(sidebarSource.includes('@contextmenu="openConversationContextMenu($event, conv.id)"'), true)
  assert.equal(rowSource.includes("@contextmenu.prevent=\"emit('contextmenu', $event)\""), true)
  assert.equal(sidebarSource.includes('const selectedConversationIds = ref(new Set())'), false)
  assert.equal(sidebarSource.includes('function toggleConversationSelection(conversationId, index)'), false)
  assert.equal(sidebarSource.includes('function selectConversationRange(index)'), false)
  assert.equal(sidebarSource.includes('Delete {{ selectedConversationIds.size }}'), false)
  assert.equal(sidebarSource.includes('pendingDeleteIds'), false)
  assert.equal(sidebarSource.includes('pendingDeleteType'), false)
})
