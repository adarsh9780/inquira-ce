import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat action rows keep wider spacing and reasoning text matches final response size', () => {
  const historySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')
  const activitySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(historySource.includes('class="space-y-3"'), true)
  assert.equal(historySource.includes('font-size: 0.875rem;'), true)
  assert.equal(historySource.includes('color: color-mix(in srgb, var(--color-text-main) 90%, var(--color-text-muted) 10%);'), true)
  assert.equal(activitySource.includes('font-size: 0.875rem;'), true)
  assert.equal(activitySource.includes('color: color-mix(in srgb, var(--color-text-main) 90%, var(--color-text-muted) 10%);'), true)
})
