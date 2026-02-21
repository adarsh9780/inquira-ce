import test from 'node:test'
import assert from 'node:assert/strict'

import { isLikelyStaleHandleError } from '../src/utils/fileHandleSupport.js'

test('detects stale handle by NotFoundError name', () => {
  const err = { name: 'NotFoundError', message: 'File not found' }
  assert.equal(isLikelyStaleHandleError(err), true)
})

test('detects stale handle by message when name is generic', () => {
  const err = { name: 'Error', message: 'No such file or directory' }
  assert.equal(isLikelyStaleHandleError(err), true)
})

test('does not flag unrelated errors as stale handle errors', () => {
  const err = { name: 'SecurityError', message: 'Permission denied by user' }
  assert.equal(isLikelyStaleHandleError(err), false)
})
