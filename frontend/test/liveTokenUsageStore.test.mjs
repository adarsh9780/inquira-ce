import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store exposes only the live token state and actions consumed by the UI', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf8')
  const source = [
    'src/stores/appStore.js',
    'src/stores/conversationStore.ts',
  ].map((path) => readFileSync(resolve(process.cwd(), path), 'utf8')).join('\n')

  assert.match(source, /const liveTokenUsage = ref[^(]*\(null\)/)
  assert.match(source, /const activeConversationUsage = ref[^(]*\(null\)/)
  assert.match(source, /const conversationUsageById = ref[^(]*\(\{\}\)/)
  assert.equal(source.includes('function setLiveTokenUsage(usage)'), true)
  assert.equal(source.includes('function setLiveTokenUsageForCurrentTurn(usage, options = {})'), true)
  assert.equal(source.includes('function setActiveConversationUsage(summary)'), true)
  assert.equal(source.includes('async function fetchActiveConversationUsage(conversationId = activeConversationId.value)'), true)
  assert.equal(source.includes('conversationApi.usage(targetConversationId)'), true)
  assert.equal(source.includes('function mergeTokenUsageTotals(base, incoming)'), true)
  assert.equal(source.includes('function resolveTokenUsageFromChatHistory(options = {})'), true)
  assert.equal(source.includes('function clearLiveTokenUsage()'), true)
  assert.equal(source.includes('function resolveLatestTokenUsageFromChatHistory(options = {})'), true)
  assert.equal(source.includes('function syncLiveTokenUsageFromChatHistory(options = {})'), true)
  assert.equal(source.includes('syncLiveTokenUsageFromChatHistory()'), true)
  assert.equal(source.includes('liveTokenUsage,'), true)
  assert.equal(source.includes('activeConversationUsage,'), true)
  assert.equal(appSource.slice(appSource.indexOf('  return {')).includes('conversationUsageById,'), false)
  assert.equal(appSource.slice(appSource.indexOf('  return {')).includes('setLiveTokenUsage,'), false)
  assert.equal(appSource.slice(appSource.indexOf('  return {')).includes('setLiveTokenUsageForCurrentTurn,'), true)
  assert.equal(appSource.slice(appSource.indexOf('  return {')).includes('setActiveConversationUsage,'), false)
  assert.equal(appSource.slice(appSource.indexOf('  return {')).includes('fetchActiveConversationUsage,'), true)
  assert.equal(appSource.slice(appSource.indexOf('  return {')).includes('clearLiveTokenUsage,'), false)
})

test('chat input applies streamed token usage as current-turn cumulative delta', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf8')

  assert.equal(source.includes('appStore.syncLiveTokenUsageFromChatHistory({ conversationId: requestConversationId })'), true)
  assert.equal(source.includes('appStore.setLiveTokenUsageForCurrentTurn(tokenUsage, { conversationId: requestConversationId })'), true)
  assert.equal(source.includes('appStore.fetchActiveConversationUsage'), true)
  assert.equal(source.includes('appStore.clearLiveTokenUsage()\\n  appStore.setLoading(true)'), false)
})
