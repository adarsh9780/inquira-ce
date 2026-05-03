import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar footer uses api and profile entry points instead of the old settings footer', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('title="API Keys"'), true)
  assert.equal(source.includes('title="Profile Settings"'), true)
  assert.equal(source.includes('title="Settings"'), false)
  assert.equal(source.includes('title="Search"'), false)
  assert.equal(source.includes('title="Terms & Conditions"'), false)
  assert.equal(source.includes('<CogIcon'), false)
})
