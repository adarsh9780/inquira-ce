import test from 'node:test'
import assert from 'node:assert/strict'

import { shouldInitializeRuntime } from '../src/utils/runtimeGate.js'

test('initializes runtime only when authenticated and not yet initialized', () => {
  assert.equal(shouldInitializeRuntime(true, false), true)
  assert.equal(shouldInitializeRuntime(false, false), false)
  assert.equal(shouldInitializeRuntime(true, true), false)
  assert.equal(shouldInitializeRuntime(false, true), false)
})
