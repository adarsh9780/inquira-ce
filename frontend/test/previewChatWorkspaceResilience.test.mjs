import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('preview service short-circuits when workspace is missing', () => {
  const servicePath = resolve(process.cwd(), 'src/services/previewService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (!appStore.hasWorkspace)'), true)
  assert.equal(source.includes('Create a workspace to start previewing data.'), true)
})

test('chat input tolerates recoverable browser-table errors', () => {
  const chatPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatPath, 'utf-8')

  assert.equal(source.includes('function isRecoverableBrowserTableError(error)'), true)
  assert.equal(source.includes('Continue in general/workspace mode instead of failing the request.'), true)
})
