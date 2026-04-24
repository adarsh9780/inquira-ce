import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store exposes pinia state/actions for live token usage updates', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf8')

  assert.equal(source.includes('const liveTokenUsage = ref(null)'), true)
  assert.equal(source.includes('function setLiveTokenUsage(usage)'), true)
  assert.equal(source.includes('function setLiveTokenUsageForCurrentTurn(usage)'), true)
  assert.equal(source.includes('function mergeTokenUsageTotals(base, incoming)'), true)
  assert.equal(source.includes('function resolveTokenUsageFromChatHistory(options = {})'), true)
  assert.equal(source.includes('function clearLiveTokenUsage()'), true)
  assert.equal(source.includes('function resolveLatestTokenUsageFromChatHistory()'), true)
  assert.equal(source.includes('function syncLiveTokenUsageFromChatHistory()'), true)
  assert.equal(source.includes('syncLiveTokenUsageFromChatHistory()'), true)
  assert.equal(source.includes('chatHistory.value = history'), true)
  assert.equal(source.includes('liveTokenUsage,'), true)
  assert.equal(source.includes('setLiveTokenUsage,'), true)
  assert.equal(source.includes('setLiveTokenUsageForCurrentTurn,'), true)
  assert.equal(source.includes('clearLiveTokenUsage,'), true)
})

test('chat input applies streamed token usage as current-turn cumulative delta', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf8')

  assert.equal(source.includes('appStore.syncLiveTokenUsageFromChatHistory()'), true)
  assert.equal(source.includes('appStore.setLiveTokenUsageForCurrentTurn(tokenUsage)'), true)
  assert.equal(source.includes('appStore.clearLiveTokenUsage()\\n  appStore.setLoading(true)'), false)
})
