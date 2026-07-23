import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input keeps stable separate voice and send controls', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('aria-label="Start voice input"'), true)
  assert.equal(source.includes('aria-label="Stop voice input"'), true)
  assert.equal(source.includes('aria-label="Send message"'), true)
  assert.equal(source.includes('aria-label="Stop generation"'), true)
  assert.equal(source.includes('@click="startVoiceInput"'), true)
  assert.equal(source.includes('@click="handleSubmit"'), true)
  assert.equal(source.includes('<MicrophoneIcon class="h-3.5 w-3.5" />'), true)
  assert.equal(source.includes('<ArrowUpIcon class="h-3 w-3" />'), true)
  assert.equal(source.includes('ArrowUpCircleIcon'), false)
  assert.equal(source.includes('StopCircleIcon'), false)
})
