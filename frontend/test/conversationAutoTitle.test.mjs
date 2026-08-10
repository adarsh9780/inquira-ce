import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('new conversations derive their title from the first submitted question', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(source.includes("import { deriveConversationTitle } from '../../utils/conversationTitle'"), true)
  assert.equal(source.match(/deriveConversationTitle\(questionText\)/g)?.length, 2)
  assert.equal(source.includes("ensureActiveConversation(workspaceStore.activeWorkspaceId, 'New chat')"), false)
})
