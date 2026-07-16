import test from 'node:test'
import assert from 'node:assert/strict'

import {
  formatCompactRelativeTimestamp,
  formatExactTimestamp,
  parseTimestamp,
} from '../src/utils/dateUtils.js'

test('parseTimestamp treats timezone-less ISO datetimes as UTC', () => {
  const parsed = parseTimestamp('2026-05-30T13:50:00')

  assert.equal(parsed?.toISOString(), '2026-05-30T13:50:00.000Z')
})

test('parseTimestamp preserves explicit timezone offsets', () => {
  const parsed = parseTimestamp('2026-05-30T13:50:00+05:30')

  assert.equal(parsed?.toISOString(), '2026-05-30T08:20:00.000Z')
})

test('formatCompactRelativeTimestamp returns short approximate labels', () => {
  const now = new Date('2026-06-23T10:00:00Z')

  assert.equal(formatCompactRelativeTimestamp('2026-06-23T09:59:00Z', now), '1m')
  assert.equal(formatCompactRelativeTimestamp('2026-06-23T08:00:00Z', now), '2h')
  assert.equal(formatCompactRelativeTimestamp('2026-06-21T10:00:00Z', now), '2d')
  assert.equal(formatCompactRelativeTimestamp('2026-06-09T10:00:00Z', now), '2w')
  assert.equal(formatCompactRelativeTimestamp('2026-05-24T10:00:00Z', now), '1mo')
  assert.equal(formatCompactRelativeTimestamp('2025-06-23T10:00:00Z', now), '1y')
})

test('formatExactTimestamp returns compact fixed exact date format', () => {
  assert.equal(formatExactTimestamp('2026-06-23T09:57:00Z'), '23 Jun 2026, 9:57 AM')
  assert.equal(formatExactTimestamp(''), 'No date available')
  assert.equal(formatExactTimestamp('not-a-date'), 'No date available')
})
