import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat markdown and code blocks include relaxed spacing rules', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('chat-markdown-content text-[14px] leading-[1.7] max-w-none'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content p)'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content strong)'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content p) {\n  margin: 0.65rem 0;\n  color: var(--color-text-main);\n}'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content li) {\n  margin: 0.35rem 0;\n  color: var(--color-text-main);\n}'), true)
  assert.equal(source.includes('margin: 0.65rem 0;'), true)
  assert.equal(source.includes(':deep(.chat-markdown-content .chat-code-block)'), true)
  assert.equal(source.includes('padding: 18px 16px;'), true)
  assert.equal(source.includes('line-height: 1.6;'), true)
})

test('chat loading status uses inline glimmer text instead of a heavy card', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('class="analyzing-status"'), true)
  assert.equal(source.includes('class="analyzing-spinner"'), true)
  assert.equal(source.includes('class="analyzing-status-text"'), true)
  assert.equal(source.includes('.analyzing-status-text::after'), true)
  assert.equal(source.includes('@keyframes analyzing-glimmer'), true)
  assert.equal(source.includes('@media (prefers-reduced-motion: reduce)'), true)
  assert.equal(source.includes('space-x-3 px-4 py-3 rounded-xl shadow-sm'), false)
})
