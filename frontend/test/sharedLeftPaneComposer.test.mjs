import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace left pane hosts a shared chat composer below both code and chat views', () => {
  const leftPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue')
  const source = readFileSync(leftPanePath, 'utf-8')

  assert.equal(source.includes("import ChatInput from '../chat/ChatInput.vue'"), true)
  assert.equal(source.includes('<ChatInput />'), true)
  assert.equal(source.includes("class=\"min-h-0 flex-1 flex flex-col p-3 sm:p-4 pb-0\""), true)
  assert.equal(source.includes("class=\"flex-shrink-0 border-t pt-2 sm:pt-3\""), true)
  assert.equal(source.includes("v-show=\"appStore.workspacePane === 'code'\""), true)
  assert.equal(source.includes("v-show=\"appStore.workspacePane === 'chat'\""), true)
})

test('chat tab keeps history content but no longer owns its own composer instance', () => {
  const chatTabPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(chatTabPath, 'utf-8')

  assert.equal(source.includes("import ChatInput from './ChatInput.vue'"), false)
  assert.equal(source.includes('<ChatInput />'), false)
  assert.equal(source.includes('data-chat-scroll-container'), true)
})
