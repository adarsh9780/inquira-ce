import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('chat submit ensures an active conversation before optimistic render and streaming', () => {
  const store = read('src/stores/appStore.js')
  const chatInput = read('src/components/chat/ChatInput.vue')

  assert.equal(store.includes('async function ensureActiveConversation(title = null)'), true)
  assert.equal(chatInput.includes("requestConversationId = String(await appStore.ensureActiveConversation('New chat') || '').trim()"), true)
  assert.equal(chatInput.includes("conversation_id: requestConversationId,"), true)
  assert.equal(chatInput.includes('conversation_id: requestConversationId || null'), false)

  const ensureIndex = chatInput.indexOf("requestConversationId = String(await appStore.ensureActiveConversation('New chat') || '').trim()")
  const optimisticIndex = chatInput.indexOf('appStore.addChatMessage(questionText, \'\', { attachments: attachmentsPayload, localMessageId, conversationId: requestConversationId })')
  assert.notEqual(ensureIndex, -1)
  assert.notEqual(optimisticIndex, -1)
  assert.equal(ensureIndex < optimisticIndex, true)
})

test('schema editor uses durable spinner class and tracks table-specific regeneration', () => {
  const schemaEditor = read('src/components/preview/SchemaEditorTab.vue')
  const styles = read('src/style.css')

  assert.equal(styles.includes('@keyframes spin'), true)
  assert.equal(styles.includes('.inquira-spinner'), true)
  assert.equal(schemaEditor.includes('const regeneratingTableName = ref(\'\')'), true)
  assert.equal(schemaEditor.includes('regeneratingTableName === group.tableName'), true)
  assert.equal(schemaEditor.includes("appStore.startBackgroundOperation({"), true)
  assert.equal(schemaEditor.includes("type: 'schema'"), true)
  assert.equal(schemaEditor.includes("regeneratingTableName.value = ''"), true)
})
