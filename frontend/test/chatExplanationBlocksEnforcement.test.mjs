import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history hides full code snapshot when explanation already contains fenced code blocks', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('function explanationHasCodeBlocks(message)'), true)
  assert.equal(source.includes('/```[a-zA-Z0-9_-]*\\n[\\s\\S]*?```/.test(explanation)'), true)
  assert.equal(source.includes('return !explanationHasCodeBlocks(message)'), true)
})
