import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history highlights autocomplete-style table column references in user questions', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('v-html="renderQuestionWithHighlights(message.question)"'), true)
  assert.equal(source.includes('const QUESTION_REFERENCE_RE = /\\b[A-Za-z_][A-Za-z0-9_]*\\."(?:[^"]|"")+"|\\b[A-Za-z_][A-Za-z0-9_]*\\.[A-Za-z_][A-Za-z0-9_]*/g'), true)
  assert.equal(source.includes('function renderQuestionWithHighlights(question)'), true)
  assert.equal(source.includes('<span class="chat-ref-highlight">'), true)
  assert.equal(source.includes(':deep(.chat-ref-highlight)'), true)
  assert.equal(source.includes('font-style: italic;'), true)
})
