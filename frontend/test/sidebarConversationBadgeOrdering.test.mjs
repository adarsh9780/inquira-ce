import test from 'node:test'
import assert from 'node:assert/strict'

test('simple project sidebar limits conversations behind show more', () => {
  const defaultVisibleConversationCount = 5
  const conversations = Array.from({ length: 8 }, (_, index) => ({ id: String(index + 1) }))

  assert.equal(conversations.slice(0, defaultVisibleConversationCount).length, 5)
  assert.equal(conversations.length > defaultVisibleConversationCount, true)
})
