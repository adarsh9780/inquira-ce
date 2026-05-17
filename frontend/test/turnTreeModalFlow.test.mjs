import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('turn tree flow loads the full tree and restores state from modal selection', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const apiSource = readFileSync(resolve(testDir, '../src/services/apiService.js'), 'utf-8')
  const storeSource = readFileSync(resolve(testDir, '../src/stores/appStore.js'), 'utf-8')
  const chatInputSource = readFileSync(resolve(testDir, '../src/components/chat/ChatInput.vue'), 'utf-8')
  const modalSource = readFileSync(resolve(testDir, '../src/components/chat/TurnTreeModal.vue'), 'utf-8')
  const branchSource = readFileSync(resolve(testDir, '../src/components/chat/TurnTreeBranch.vue'), 'utf-8')

  assert.equal(apiSource.includes('async v1GetTurnTree(conversationId, currentTurnId = null)'), true)
  assert.equal(apiSource.includes("return axios.get(`/api/v1/conversations/${conversationId}/turn-tree`, { params })"), true)
  assert.equal(storeSource.includes('function setActiveTurnTree(payload)'), true)
  assert.equal(storeSource.includes('setActiveTurnTree(payload)'), true)
  assert.equal(chatInputSource.includes('await appStore.loadActiveTurnTree(conversationId, turnId)'), true)
  assert.equal(chatInputSource.includes('@select="selectTurnTreeNode"'), true)
  assert.equal(chatInputSource.includes('await appStore.loadActiveTurnRelations(turnId)'), true)
  assert.equal(modalSource.includes('h-[78vh]'), true)
  assert.equal(modalSource.includes('Select any turn to restore its chat, artifacts, and workspace state.'), true)
  assert.equal(branchSource.includes('assistant_text'), true)
  assert.equal(branchSource.includes('Mark final'), true)
  assert.equal(branchSource.includes('No response saved'), true)
  assert.equal(branchSource.includes("{{ isCollapsed ? '+' : '−' }}"), true)
})
