import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input consumes live token events and does not fall back to non-stream analyze route', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatInputPath, 'utf-8')

  assert.equal(source.includes("evt.event === 'token'"), true)
  assert.equal(source.includes('streamedExplanation += evt.data.text'), true)
  assert.equal(source.includes('if (hasTokenStream) return'), true)
  assert.equal(source.includes('response = await apiService.v1Analyze('), false)
})

test('v1AnalyzeStream always uses stream endpoint without local non-stream fallback', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (!isStreamingEnabled()) {'), false)
  assert.equal(source.includes('disableStreamingForUnsupportedStatus(response.status)'), false)
  assert.equal(source.includes('${v1Api.chat.stream}'), true)
})
