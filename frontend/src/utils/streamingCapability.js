let streamingEnabled = true

export function isStreamingEnabled() {
  return streamingEnabled
}

export function disableStreamingForUnsupportedStatus(status) {
  if (status === 404 || status === 405) {
    streamingEnabled = false
  }
}

export function resetStreamingCapabilityForTests() {
  streamingEnabled = true
}
