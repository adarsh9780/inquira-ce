import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat tab uses compact header controls and history modal', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('ConversationHistoryModal'), true)
  assert.equal(source.includes('title="Conversation history"'), true)
  assert.equal(source.includes('<h3 class="text-sm font-semibold text-gray-700">Conversations</h3>'), false)
})
