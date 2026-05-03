import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar row hover background uses the same token as user chat bubble', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')
  const chatSource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(styleSource.includes('--color-chat-user-bubble:'), true)
  assert.equal(chatSource.includes('background-color: var(--color-chat-user-bubble);'), true)
  assert.equal(sidebarSource.includes('background-color: var(--color-selected-surface);'), true)
})
