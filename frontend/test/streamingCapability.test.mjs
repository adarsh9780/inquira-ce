import test from 'node:test'
import assert from 'node:assert/strict'
import {
  disableStreamingForUnsupportedStatus,
  isStreamingEnabled,
  resetStreamingCapabilityForTests
} from '../src/utils/streamingCapability.js'

test('streaming remains enabled for non-unsupported statuses', () => {
  resetStreamingCapabilityForTests()
  disableStreamingForUnsupportedStatus(500)
  assert.equal(isStreamingEnabled(), true)
})

test('streaming is disabled for 404 and stays disabled', () => {
  resetStreamingCapabilityForTests()
  disableStreamingForUnsupportedStatus(404)
  assert.equal(isStreamingEnabled(), false)
  disableStreamingForUnsupportedStatus(200)
  assert.equal(isStreamingEnabled(), false)
})

test('streaming is disabled for 405', () => {
  resetStreamingCapabilityForTests()
  disableStreamingForUnsupportedStatus(405)
  assert.equal(isStreamingEnabled(), false)
})
