import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat autocomplete stays dismissed after Escape for the same token context', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(source.includes("const dismissedSuggestionSignature = ref('')"), true)
  assert.equal(source.includes('function buildSuggestionDismissSignature(text = question.value, cursor = currentCursorPosition())'), true)
  assert.equal(source.includes('dismissedSuggestionSignature.value = buildSuggestionDismissSignature()'), true)
  assert.equal(source.includes('dismissedSuggestionSignature.value === signature'), true)
  assert.equal(source.includes("const signature = `${range.start}:${range.end}:${token}:${value}`"), true)
})
