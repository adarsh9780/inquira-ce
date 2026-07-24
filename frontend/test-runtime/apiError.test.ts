import { expect, test } from 'vitest'

import { extractApiErrorMessage, extractApiErrorMessageFromPayload } from '../src/utils/apiError'

test('extracts string detail from backend error payload', () => {
  const err = {
    response: {
      data: {
        detail: 'Schema path not configured. Please set your data path.'
      }
    }
  }

  expect(extractApiErrorMessage(err, 'fallback')).toBe(
    'Schema path not configured. Please set your data path.',
  )
})

test('extracts validation detail list with msg field', () => {
  const err = {
    response: {
      data: {
        detail: [{ type: 'missing', msg: 'Field required', loc: ['body', 'question'] }]
      }
    }
  }

  expect(extractApiErrorMessage(err, 'fallback')).toBe('Field required')
})

test('falls back to generic message when no detail is present', () => {
  const err = { message: '' }
  expect(extractApiErrorMessage(err, 'fallback')).toBe('fallback')
})

test('extracts nested detail from stringified backend json payload', () => {
  expect(
    extractApiErrorMessageFromPayload('{"detail":"Agent stream error: internal provider failure"}', 'fallback'),
  ).toBe('Agent stream error: internal provider failure')
})
