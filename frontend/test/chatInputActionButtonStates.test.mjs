import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input exposes independent stop-generation and voice-input states', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('handleActionButtonClick'), false)
  assert.equal(source.includes('v-if="isVoiceInputActive"'), true)
  assert.equal(source.includes('class="btn-icon voice-input-pulse"'), true)
  assert.equal(source.includes('@click="stopVoiceInput"'), true)
  assert.equal(source.includes('@click="handleStopGeneration"'), true)
  assert.equal(source.includes('v-if="executionStore.isConversationRunning(conversationStore.activeConversationId)"'), true)
  assert.equal(source.includes('executionStore.abortConversationRun(conversationId)'), true)
  assert.equal(source.includes('stoppedConversationIds'), true)
  assert.equal(source.includes('window.SpeechRecognition || window.webkitSpeechRecognition'), true)
  assert.equal(source.includes('Voice input unavailable on this device/browser'), true)
  assert.equal(source.includes('Microphone permission is required for voice input.'), true)
})
