import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input action button supports stop and voice-input states', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('handleActionButtonClick'), true)
  assert.equal(source.includes('<StopCircleIcon v-if="appStore.isLoading"'), true)
  assert.equal(source.includes('v-else-if="isVoiceInputActive"'), true)
  assert.equal(source.includes('w-[22px] h-[22px] items-center justify-center rounded-full bg-zinc-900 text-white animate-pulse'), true)
  assert.equal(source.includes('v-else-if="isComposerEmpty"'), true)
  assert.equal(source.includes('<MicrophoneIcon class="w-3 h-3" />'), true)
  assert.equal(source.includes('activeAbortController.value?.abort()'), true)
  assert.equal(source.includes('window.SpeechRecognition || window.webkitSpeechRecognition'), true)
  assert.equal(source.includes('Voice input unavailable on this device/browser'), true)
  assert.equal(source.includes('Microphone permission is required for voice input.'), true)
})
