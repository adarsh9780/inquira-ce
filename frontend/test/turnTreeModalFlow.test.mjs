import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('sidebar turn tree flow loads the full tree and restores state from selection', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const apiSource = readFileSync(resolve(testDir, '../src/services/apiService.js'), 'utf-8')
  const storeSource = readFileSync(resolve(testDir, '../src/stores/appStore.js'), 'utf-8')
  const globalTreeSource = readFileSync(resolve(testDir, '../src/components/layout/sidebar/SidebarGlobalTurnTree.vue'), 'utf-8')
  const graphViewSource = readFileSync(resolve(testDir, '../src/components/chat/TurnTreeGraphView.vue'), 'utf-8')
  const treeActionsSource = readFileSync(resolve(testDir, '../src/components/chat/TurnTreeNodeActions.vue'), 'utf-8')

  assert.equal(apiSource.includes('async v1GetTurnTree(conversationId, currentTurnId = null)'), true)
  assert.equal(apiSource.includes("return axios.get(`/api/v1/conversations/${conversationId}/turn-tree`, { params })"), true)
  assert.equal(storeSource.includes('function setActiveTurnTree(payload)'), true)
  assert.equal(storeSource.includes('setActiveTurnTree(payload)'), true)
  assert.equal(globalTreeSource.includes('appStore.loadWorkspaceTurnTree()'), true)
  assert.equal(globalTreeSource.includes(':current-parent-turn-id="appStore.activeTurnRelations?.parent?.id || \'\'"'), true)
  assert.equal(globalTreeSource.includes('@select="selectTurn"'), true)
  assert.equal(globalTreeSource.includes('await appStore.loadActiveTurnRelations(targetTurnId)'), true)
  assert.equal(globalTreeSource.includes("appStore.setActiveTab('workspace')"), true)
  assert.equal(graphViewSource.includes('TurnTreeNodeActions'), true)
  assert.equal(treeActionsSource.includes('data-turn-tree-context-menu'), true)
  assert.equal(treeActionsSource.includes('View Details'), true)
  assert.equal(treeActionsSource.includes('await apiService.v1GetTurn(conversationId, turnId)'), true)
  assert.equal(treeActionsSource.includes("emit('delete-turn', { conversationId, turnId })"), true)
  assert.equal(graphViewSource.includes("emit('move-turn'"), false)
  assert.equal(graphViewSource.includes('assistant_text'), true)
  assert.equal(graphViewSource.includes('@contextmenu.prevent="openNodeMenu'), true)
  assert.equal(graphViewSource.includes('No response saved'), true)
  assert.equal(graphViewSource.includes('@wheel.prevent="handleWheel'), true)
  assert.equal(graphViewSource.includes('currentParentTurnId'), true)
})
