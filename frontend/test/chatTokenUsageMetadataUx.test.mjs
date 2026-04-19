import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar renders provider token usage from pinia and shows price when available', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf8')

  assert.equal(source.includes('appStore.liveTokenUsage'), true)
  assert.equal(source.includes('tokenUsageSummaryLabel'), true)
  assert.equal(source.includes("`in ${inputTokens.toLocaleString()}`"), true)
  assert.equal(source.includes("`cached ${cachedInputTokens.toLocaleString()}`"), true)
  assert.equal(source.includes("`out ${outputTokens.toLocaleString()}`"), true)
  assert.equal(source.includes('formatUsd'), true)
})

test('chat history no longer renders token usage footer', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf8')

  assert.equal(source.includes('tokenUsageText(message)'), false)
  assert.equal(source.includes('token-usage-line'), false)
})
