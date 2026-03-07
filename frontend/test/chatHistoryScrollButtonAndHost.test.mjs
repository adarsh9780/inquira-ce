import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history binds scroll logic to outer scroll host and forces initial bottom alignment', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('scrollHost.value = resolveScrollHost()'), true)
  assert.equal(source.includes("localContainer.parentElement?.closest?.('[data-chat-scroll-container]')"), true)
  assert.equal(source.includes("window.setTimeout(() => scrollToBottom({ behavior: 'auto', force: true }), 32)"), true)
})

test('chat history renders conditional scroll-to-bottom button when user scrolls up', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('v-if="showScrollToBottomButton"'), true)
  assert.equal(source.includes('aria-label="Scroll to bottom"'), true)
  assert.equal(source.includes('@click="handleScrollToBottomClick"'), true)
  assert.equal(source.includes('const showScrollToBottomButton = ref(false)'), true)
  assert.equal(source.includes('function handleScrollToBottomClick() {'), true)
  assert.equal(source.includes("scrollToBottom({ behavior: 'smooth', force: true })"), true)
})
