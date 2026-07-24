import { expect, test } from 'vitest'

import {
  formatCompactRelativeTimestamp,
  formatExactTimestamp,
  parseTimestamp,
} from '../src/utils/dateUtils'

test('parseTimestamp treats timezone-less ISO datetimes as UTC', () => {
  const parsed = parseTimestamp('2026-05-30T13:50:00')

  expect(parsed?.toISOString()).toBe('2026-05-30T13:50:00.000Z')
})

test('parseTimestamp preserves explicit timezone offsets', () => {
  const parsed = parseTimestamp('2026-05-30T13:50:00+05:30')

  expect(parsed?.toISOString()).toBe('2026-05-30T08:20:00.000Z')
})

test('formatCompactRelativeTimestamp returns short approximate labels', () => {
  const now = new Date('2026-06-23T10:00:00Z')

  expect(formatCompactRelativeTimestamp('2026-06-23T09:59:00Z', now)).toBe('1m')
  expect(formatCompactRelativeTimestamp('2026-06-23T08:00:00Z', now)).toBe('2h')
  expect(formatCompactRelativeTimestamp('2026-06-21T10:00:00Z', now)).toBe('2d')
  expect(formatCompactRelativeTimestamp('2026-06-09T10:00:00Z', now)).toBe('2w')
  expect(formatCompactRelativeTimestamp('2026-05-24T10:00:00Z', now)).toBe('1mo')
  expect(formatCompactRelativeTimestamp('2025-06-23T10:00:00Z', now)).toBe('1y')
})

test('formatExactTimestamp returns compact fixed exact date format', () => {
  expect(formatExactTimestamp('2026-06-23T09:57:00Z')).toBe('23 Jun 2026, 9:57 AM')
  expect(formatExactTimestamp('')).toBe('No date available')
  expect(formatExactTimestamp('not-a-date')).toBe('No date available')
})
