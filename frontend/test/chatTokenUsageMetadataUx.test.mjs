import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar renders provider token placeholders from pinia and formats price', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf8')

  assert.equal(source.includes('appStore.liveTokenUsage'), true)
  assert.equal(source.includes('tokenUsageSummaryLabel'), true)
  assert.equal(source.includes('formatTokenCount'), true)
  assert.equal(source.includes("if (!Number.isInteger(parsed)) return '-'"), true)
  assert.equal(source.includes("if (typeof amount !== 'number') return '$-'"), true)
  assert.equal(source.includes("`in ${inputTokens}`"), true)
  assert.equal(source.includes("`cached ${cachedInputTokens}`"), true)
  assert.equal(source.includes("`out ${outputTokens}`"), true)
  assert.equal(source.includes('formatUsd'), true)
  assert.equal(source.includes('v-if="authStore.isAuthenticated" class="flex items-center gap-1 h-full px-1 text-[10px]'), true)
})

test('chat history no longer renders token usage footer', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf8')

  assert.equal(source.includes('tokenUsageText(message)'), false)
  assert.equal(source.includes('token-usage-line'), false)
})
