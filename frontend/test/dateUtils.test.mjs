import test from 'node:test'
import assert from 'node:assert/strict'

import { parseTimestamp } from '../src/utils/dateUtils.js'

test('parseTimestamp treats timezone-less ISO datetimes as UTC', () => {
  const parsed = parseTimestamp('2026-05-30T13:50:00')

  assert.equal(parsed?.toISOString(), '2026-05-30T13:50:00.000Z')
})

test('parseTimestamp preserves explicit timezone offsets', () => {
  const parsed = parseTimestamp('2026-05-30T13:50:00+05:30')

  assert.equal(parsed?.toISOString(), '2026-05-30T08:20:00.000Z')
})
