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
  assert.equal(source.includes('const activeStillExists = currentActiveId'), true)
  assert.equal(source.includes('await fetchConversationTurns({ reset: true })'), true)
  assert.equal(source.includes('setActiveConversationId(fallbackConversationId)'), true)
})

test('sidebar conversation rows use an ellipsis menu and route deletes through store sync action', () => {
  const sidebarSource = readSource('src/components/layout/UnifiedSidebar.vue')
  const chatTabSource = readSource('src/components/chat/ChatTab.vue')

  assert.equal(sidebarSource.includes('EllipsisHorizontalIcon'), true)
  assert.equal(sidebarSource.includes('toggleConversationMenu($event, conv.id)'), true)
  assert.equal(sidebarSource.includes('data-conversation-actions-menu'), true)
  assert.equal(sidebarSource.includes('v-if="conversationMenuId"'), true)
  assert.equal(sidebarSource.includes(':style="conversationMenuStyle"'), true)
  assert.equal(sidebarSource.includes('function openSingleConversationMenu(conversationId, position)'), true)
  assert.equal(sidebarSource.includes('startEditingFromMenu(activeConversationMenuTarget)'), true)
  assert.equal(sidebarSource.includes('confirmDeleteConversation(conversationMenuId)'), true)
  assert.equal(sidebarSource.includes('await appStore.deleteConversationById(pendingDeleteId.value)'), true)
  assert.equal(sidebarSource.includes('await apiService.v1DeleteConversation(pendingDeleteId.value)'), false)
  assert.equal(chatTabSource.includes('title="Delete Conversation"'), false)
})

test('sidebar supports multi-select conversation deletion with range selection', () => {
  const sidebarSource = readSource('src/components/layout/UnifiedSidebar.vue')

  assert.equal(sidebarSource.includes('@click="handleConversationClick($event, conv.id, index)"'), true)
  assert.equal(sidebarSource.includes('@contextmenu.prevent="openConversationContextMenu($event, conv.id)"'), true)
  assert.equal(sidebarSource.includes('const selectedConversationIds = ref(new Set())'), true)
  assert.equal(sidebarSource.includes('function toggleConversationSelection(conversationId, index)'), true)
  assert.equal(sidebarSource.includes('function selectConversationRange(index)'), true)
  assert.equal(sidebarSource.includes("if (event?.shiftKey)"), true)
  assert.equal(sidebarSource.includes('event?.ctrlKey || event?.metaKey'), true)
  assert.equal(sidebarSource.includes('function confirmDeleteSelectedConversations()'), true)
  assert.equal(sidebarSource.includes("pendingDeleteType.value   = 'conversations'"), true)
  assert.equal(sidebarSource.includes("await appStore.deleteConversationById(id)"), true)
  assert.equal(sidebarSource.includes('Delete {{ selectedConversationIds.size }}'), true)
  assert.equal(sidebarSource.includes('openSingleConversationMenu(id, clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 128, 88))'), true)
  assert.equal(sidebarSource.includes('data-conversation-actions-menu'), true)
})
