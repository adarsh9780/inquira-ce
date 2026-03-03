import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat markdown and code blocks include relaxed spacing rules', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('chat-markdown-content text-sm leading-relaxed prose prose-sm'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content p)'), true)
  assert.equal(source.includes('margin: 0.65rem 0;'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content .chat-code-block)'), true)
  assert.equal(source.includes('padding: 18px 16px;'), true)
  assert.equal(source.includes('line-height: 1.62;'), true)
})
