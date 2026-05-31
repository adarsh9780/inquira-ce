import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar adds workspace view entries and uses numbered conversation badges', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('@click="openChat"'), false)
  assert.equal(sidebarSource.includes('@click="openSchemaEditor"'), true)
  assert.equal(sidebarSource.includes('@click="openConversationTree"'), true)
  assert.equal(sidebarSource.includes('ChatBubbleLeftRightIcon'), false)
  assert.equal(sidebarSource.includes('CircleStackIcon'), true)
  assert.equal(sidebarSource.includes('QueueListIcon'), true)
  assert.equal(sidebarSource.includes('Schema'), true)
  assert.equal(sidebarSource.includes('Conversation Tree'), true)
  assert.equal(sidebarSource.includes('Conversations and analysis'), false)
  assert.equal(sidebarSource.includes('Datasets and column metadata'), true)
  assert.equal(sidebarSource.includes('Turns across this workspace'), true)
  assert.equal(sidebarSource.indexOf('<!-- ─── Workspace Views ─── -->') > sidebarSource.indexOf('<!-- ─── Conversations ─── -->'), true)
  assert.equal(sidebarSource.indexOf('<!-- ─── Footer Navigation ─── -->') > sidebarSource.indexOf('<!-- ─── Workspace Views ─── -->'), true)
  assert.equal(sidebarSource.includes(`v-if="appStore.activeTab === 'workspace'"`), false)
  assert.equal(sidebarSource.includes('min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-1 custom-scrollbar'), true)
  assert.equal(sidebarSource.includes('max-h-[11.75rem] flex-none overflow-y-auto overflow-x-hidden pb-1'), false)
  assert.equal(sidebarSource.includes('<SidebarConversations'), false)
  assert.equal(sidebarSource.includes("appStore.isSidebarCollapsed ? 'justify-center px-0 py-1.5' : 'justify-start px-3 py-1.5'"), true)
  assert.equal(sidebarSource.includes('conversationBadgeLabel(index, appStore.conversations.length)'), true)
  assert.equal(sidebarSource.includes('conversation?.last_turn_at || conversation?.updated_at || conversation?.created_at'), true)
  assert.equal(sidebarSource.includes("return 'Running...'"), true)
  assert.equal(sidebarSource.includes('const ordinal = total - offset'), true)
  assert.equal(sidebarSource.includes("if (ordinal > 99) return '99+'"), true)
  assert.equal(sidebarSource.includes('rounded-md bg-[var(--color-accent)]/10'), false)
  assert.equal(sidebarSource.includes('rounded-md bg-[var(--color-selected-surface)]'), false)
  assert.equal(sidebarSource.includes('text-[11px] font-semibold leading-none tabular-nums'), true)
  assert.equal(sidebarSource.includes('bg-[var(--color-accent)] text-white'), false)
})

test('activating a conversation returns the shell to workspace chat', () => {
  const storeSource = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')
  const globalTreeSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarGlobalTurnTree.vue'), 'utf-8')

  assert.equal(storeSource.includes("function setActiveConversationId(conversationId) {"), true)
  assert.equal(storeSource.includes("activeTab.value = 'workspace'"), true)
  assert.equal(storeSource.includes("workspacePane.value = 'chat'"), true)
  assert.equal(globalTreeSource.includes('if (targetConversationId !== appStore.activeConversationId) {'), true)
  assert.equal(globalTreeSource.includes('appStore.setActiveConversationId(targetConversationId)'), true)
  assert.equal(globalTreeSource.includes("appStore.setActiveTab('workspace')"), true)
  assert.equal(globalTreeSource.includes('await appStore.fetchConversationTurns({ reset: true })'), true)
})
