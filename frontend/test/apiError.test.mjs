import test from 'node:test'
import assert from 'node:assert/strict'

import { extractApiErrorMessage } from '../src/utils/apiError.js'

test('extracts string detail from backend error payload', () => {
  const err = {
    response: {
      data: {
        detail: 'Schema path not configured. Please set your data path.'
      }
    }
  }

  assert.equal(
    extractApiErrorMessage(err, 'fallback'),
    'Schema path not configured. Please set your data path.'
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

  assert.equal(extractApiErrorMessage(err, 'fallback'), 'Field required')
})

test('falls back to generic message when no detail is present', () => {
  const err = { message: '' }
  assert.equal(extractApiErrorMessage(err, 'fallback'), 'fallback')
})
