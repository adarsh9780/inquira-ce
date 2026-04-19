import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history renders provider token usage footer only when metadata token_usage exists', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'),
    'utf8'
  )

  assert.equal(source.includes('tokenUsageText(message)'), true)
  assert.equal(source.includes('metadata.token_usage'), true)
  assert.equal(source.includes('Tokens:'), true)
})
