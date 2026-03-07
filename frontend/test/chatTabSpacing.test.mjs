import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat tab uses slightly tighter content padding around chat history', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('px-2.5 sm:px-3.5 pt-2.5 sm:pt-3.5 pb-2 sm:pb-2.5'), true)
})
