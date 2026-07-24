import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('tool output preview uses user-facing label for json payloads', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolOutputPreview.vue'), 'utf-8')
  assert.equal(source.includes("if (kind === 'json') return 'Tool details'"), true)
  assert.equal(source.includes("if (kind === 'json') return 'Structured output'"), false)
})
