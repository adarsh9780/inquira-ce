import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input maps stream errors using fetch-style error.status fallback', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatInputPath, 'utf-8')

  assert.equal(source.includes('const status = Number(error?.response?.status ?? error?.status ?? 0)'), true)
  assert.equal(source.includes('status >= 500'), true)
})
