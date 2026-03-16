import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input supports image attachment selection and multimodal submit payloads', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('ref="attachmentInputRef"'), true)
  assert.equal(source.includes('multiple'), true)
  assert.equal(source.includes('handleAttachmentDrop'), true)
  assert.equal(source.includes('preferred_table_name: schemaPayload.tableName'), true)
  assert.equal(source.includes('attachments: attachmentsPayload'), true)
  assert.equal(source.includes('appStore.setLastMessageAnalysisMetadata(response?.metadata || {})'), true)
})
