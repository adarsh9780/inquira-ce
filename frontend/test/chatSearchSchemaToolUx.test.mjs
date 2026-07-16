import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('tool activity card summarizes search_schema with query and match count', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(source.includes("if (normalized === 'search_schema')"), true)
  assert.equal(source.includes('firstText(args.query)'), true)
  assert.equal(source.includes('output.match_count'), true)
  assert.equal(source.includes('Array.isArray(output.columns)'), true)
  assert.equal(source.includes('Searching schema for "${query}" (${count} matches)'), true)
})

test('tool activity card no longer has inspect_schema summary branch', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(source.includes("normalized === 'inspect_schema'"), false)
  assert.equal(source.includes("normalized === 'input_schema'"), false)
})
