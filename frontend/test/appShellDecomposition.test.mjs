import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('App delegates desktop startup presentation to a focused component', () => {
  const app = read('src/App.vue')
  const startupGate = read('src/components/startup/DesktopStartupGate.vue')

  assert.match(app, /import DesktopStartupGate/)
  assert.match(app, /<DesktopStartupGate/)
  assert.match(app, /@restart="restartDesktopApp"/)
  assert.match(startupGate, /role="status"/)
  assert.match(startupGate, /role="alert"/)
  assert.match(startupGate, /<StartupFailureActions/)
})

test('chat components delegate attachments and scroll-follow lifecycles to composables', () => {
  const input = read('src/components/chat/ChatInput.vue')
  const history = read('src/components/chat/ChatHistory.vue')
  const attachments = read('src/composables/useChatAttachments.js')
  const scroll = read('src/composables/useChatScrollFollow.js')

  assert.match(input, /useChatAttachments\(\{/)
  assert.match(attachments, /async function appendPendingAttachments/)
  assert.match(history, /useChatScrollFollow\(\{/)
  assert.match(scroll, /MutationObserver/)
  assert.match(scroll, /watch\(activeConversationId/)
})
