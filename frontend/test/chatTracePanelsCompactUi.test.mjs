import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history renders compact trace panels and editor-only code hint', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('Analysis trace'), true)
  assert.equal(source.includes('Code updated in editor.'), true)
  assert.equal(source.includes('@click="openCodePane"'), true)
  assert.equal(source.includes('max-h-56 overflow-auto'), true)
  assert.equal(source.includes('max-h-48 overflow-auto'), true)
  assert.equal(source.includes('message.codeSnapshot'), false)
})
