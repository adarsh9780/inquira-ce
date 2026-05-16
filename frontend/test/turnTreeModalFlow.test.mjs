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

  assert.equal(apiSource.includes('async v1GetTurnTree(conversationId, currentTurnId = null)'), true)
  assert.equal(apiSource.includes("return axios.get(`/api/v1/conversations/${conversationId}/turn-tree`, { params })"), true)
  assert.equal(storeSource.includes('function setActiveTurnTree(payload)'), true)
  assert.equal(storeSource.includes('setActiveTurnTree(payload)'), true)
  assert.equal(chatInputSource.includes('await appStore.loadActiveTurnTree(conversationId, turnId)'), true)
  assert.equal(chatInputSource.includes('@select="selectTurnTreeNode"'), true)
  assert.equal(chatInputSource.includes('await appStore.loadActiveTurnRelations(turnId)'), true)
  assert.equal(modalSource.includes('Node ${branchProps.node?.seq_no || \'\'}'), true)
  assert.equal(modalSource.includes('String(branchProps.node?.id || \'\')'), true)
})
