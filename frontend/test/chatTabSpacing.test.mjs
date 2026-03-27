import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat tab uses slightly tighter content padding around chat history', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('class="px-2 sm:px-2 pt-2 pb-1 space-y-2"'), true)
})
