import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat tab uses compact header controls without history modal', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('ConversationHistoryModal'), false)
  assert.equal(source.includes('title="Conversation history"'), false)
  assert.equal(source.includes('title="New Conversation"'), true)
  assert.equal(source.includes('title="Clear Conversation"'), true)
  assert.equal(source.includes('title="Delete Conversation"'), true)
  assert.equal(source.includes('<h3 class="text-sm font-semibold text-gray-700">Conversations</h3>'), false)
  assert.equal(source.includes('flex flex-wrap items-center'), false)
  assert.equal(source.includes('overflow-x-auto'), false)
  assert.equal(source.includes('flex items-center gap-1 bg-gray-50 p-1 rounded-xl border border-gray-100'), true)
  assert.equal(source.includes('class="min-w-0 truncate text-sm font-bold text-gray-900'), false)
  assert.equal(source.includes('class="flex-1 min-h-0 overflow-y-auto bg-gray-50/30"'), true)
})
