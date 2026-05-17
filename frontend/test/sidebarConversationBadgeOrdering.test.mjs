import test from 'node:test'
import assert from 'node:assert/strict'

function conversationBadgeLabel(index, totalCount) {
  const total = Number(totalCount)
  const offset = Number(index)
  const ordinal = total - offset
  if (!Number.isFinite(ordinal) || ordinal <= 0) return '1'
  if (ordinal > 99) return '99+'
  return String(ordinal)
}

test('conversation badge numbering stays stable while newest conversations render first', () => {
  assert.equal(conversationBadgeLabel(0, 3), '3')
  assert.equal(conversationBadgeLabel(1, 3), '2')
  assert.equal(conversationBadgeLabel(2, 3), '1')
})
