import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('native bridge exposes durable conversation usage', () => {
  const apiService = read('src/api/conversations.ts')

  assert.equal(apiService.includes('usage(conversationId'), true)
  assert.equal(apiService.includes("invokeNative<RecordValue>('GetConversationUsage'"), true)
})

test('native turn history uses the bounded Go page endpoint', () => {
  const apiService = read('src/api/conversations.ts')

  assert.equal(apiService.includes("invokeNative<RecordValue>(\n      'ListConversationTurnPage'"), true)
  assert.equal(apiService.includes('Number(limit || 5)'), true)
  assert.equal(apiService.includes("Number(limit || 5),\n      '',"), true)
})

test('native conversation tree carries turn and conversation usage', () => {
  const apiService = read('src/api/conversations.ts')

  assert.equal(apiService.includes('usage: (turn.metadata as RecordValue | undefined)?.token_usage || null'), true)
  assert.equal(apiService.includes('app.GetConversationUsage(String(item.id || \'\'))'), true)
  assert.equal(apiService.includes('usage_summary: usageSummary'), true)
})

test('status bar and store use full active conversation usage aggregate', () => {
  const statusBar = read('src/components/layout/StatusBar.vue')
  const store = read('src/stores/appStore.js')

  assert.equal(statusBar.includes('appStore.activeConversationUsage'), true)
  assert.equal(statusBar.includes('formatUsageCompact'), true)
  assert.equal(store.includes('activeConversationUsage'), true)
  assert.equal(store.includes('conversationUsageById'), true)
  assert.equal(store.includes('await fetchActiveConversationUsage(targetConversationId)'), true)
})

test('turn details and conversation graph render usage summaries', () => {
  const treeActions = read('src/components/chat/TurnTreeNodeActions.vue')
  const graph = read('src/components/chat/TurnTreeGraphView.vue')

  assert.equal(treeActions.includes('detailTurn.value?.metadata?.token_usage'), true)
  assert.equal(treeActions.includes('detailUsageLabel'), true)
  assert.equal(graph.includes('conversation?.usage_summary'), true)
  assert.equal(graph.includes('conversationUsageLabel(conversation)'), true)
  assert.equal(graph.includes('nodeUsageTooltip(node)'), true)
})

test('shortcut registry drives global shortcuts and keyboard shortcuts panel', () => {
  const shortcuts = read('src/utils/keyboardShortcuts.js')
  const app = read('src/App.vue')
  const sidebar = read('src/components/layout/UnifiedSidebar.vue')
  const modal = read('src/components/modals/KeyboardShortcutsModal.vue')

  for (const id of ['conversation-tree', 'schema', 'settings', 'dataset-import', 'command-palette', 'sidebar', 'terminal']) {
    assert.equal(shortcuts.includes(`id: '${id}'`), true)
    assert.equal(app.includes(`matchShortcut(event, '${id}')`), true)
  }
  assert.equal(shortcuts.includes("id: 'keyboard-shortcuts'"), false)
  assert.equal(shortcuts.includes("id: 'layout-cycle'"), false)
  assert.equal(sidebar.includes('Keyboard Shortcuts'), true)
  assert.equal(sidebar.includes("shortcutTooltip('keyboard-shortcuts'"), false)
  assert.equal(sidebar.includes('KeyboardShortcutsModal'), false)
  assert.equal(app.includes('KeyboardShortcutsModal'), true)
  assert.equal(sidebar.includes("shortcutTooltip('schema'"), true)
  assert.equal(sidebar.includes("shortcutTooltip('conversation-tree'"), true)
  assert.equal(modal.includes('shortcutsByCategory'), true)
  assert.equal(modal.includes('shortcutLabel(shortcut, platform)'), true)
})
