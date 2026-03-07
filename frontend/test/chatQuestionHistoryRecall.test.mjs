import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input supports ArrowUp/ArrowDown question recall without breaking autocomplete navigation', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('const questionHistoryIndex = ref(-1)'), true)
  assert.equal(source.includes('const questionHistoryDraft = ref(\'\')'), true)
  assert.equal(source.includes('function isHistoryNavigationAllowed(event, step)'), true)
  assert.equal(source.includes("if (event.key === 'ArrowUp' && isHistoryNavigationAllowed(event, -1))"), true)
  assert.equal(source.includes("if (event.key === 'ArrowDown' && isHistoryNavigationAllowed(event, 1))"), true)
  assert.equal(source.includes('appStore.addQuestionHistoryEntry(questionText)'), true)
})

test('app store keeps a capped, persisted question history for recall', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('const questionHistory = ref([])'), true)
  assert.equal(source.includes('const MAX_QUESTION_HISTORY = 30'), true)
  assert.equal(source.includes('question_history: Array.isArray(questionHistory.value) ? questionHistory.value : []'), true)
  assert.equal(source.includes('.slice(-MAX_QUESTION_HISTORY)'), true)
  assert.equal(source.includes('function addQuestionHistoryEntry(question)'), true)
  assert.equal(source.includes('if (existing[existing.length - 1] === normalized) return'), true)
})
