import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat response hydrates editor content directly from code/current_code payload', () => {
  const chatPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatPath, 'utf-8')

  assert.equal(source.includes('const finalCode = (code ?? current_code ?? \'\').toString()'), true)
  assert.equal(source.includes('finalStatePatch.generatedCode = finalCode'), true)
  assert.equal(source.includes('finalStatePatch.pythonFileContent = finalCode'), true)
  assert.equal(source.includes('applyConversationResultState(requestConversationId, finalStatePatch'), true)
})
