import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar renders provider token placeholders from pinia and formats price', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf8')
  const formatter = readFileSync(resolve(process.cwd(), 'src/utils/usageFormat.js'), 'utf8')

  assert.equal(source.includes('appStore.activeConversationUsage'), true)
  assert.equal(source.includes('appStore.liveTokenUsage'), true)
  assert.equal(source.includes('tokenUsageSummaryLabel'), true)
  assert.equal(source.includes('tokenUsageHoverLabel'), true)
  assert.equal(source.includes('formatUsageCompact'), true)
  assert.equal(source.includes('formatUsageTooltip'), true)
  assert.equal(formatter.includes("return `In ${formatTokenCount(usage.input_tokens)} | Out ${formatTokenCount(usage.output_tokens)} | Cost ${formatUsd(usage.price_usd)}`"), true)
  assert.equal(formatter.includes('Input tokens:'), true)
  assert.equal(formatter.includes('Cached input tokens:'), true)
  assert.equal(formatter.includes('Output tokens:'), true)
  assert.equal(formatter.includes('Cost unavailable'), true)
  assert.equal(source.includes(':title="tokenUsageHoverLabel"'), true)
  assert.equal(source.includes('v-if="authStore.isAuthenticated"'), true)
  assert.equal(source.includes('class="flex items-center gap-1 h-full px-1 text-[10px] text-[var(--color-text-muted)]"'), true)
})

test('chat history no longer renders token usage footer', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf8')

  assert.equal(source.includes('tokenUsageText(message)'), false)
  assert.equal(source.includes('token-usage-line'), false)
})
