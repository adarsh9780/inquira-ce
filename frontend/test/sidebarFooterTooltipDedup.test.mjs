import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar rail removes the old settings footer and adds profile and llm entry points', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  assert.equal(source.includes('title="Create Workspace"'), true)
  assert.equal(source.includes('title="LLM & API Keys"'), true)
  assert.equal(source.includes('title="User Profile"'), true)

  assert.equal(source.includes('aria-label="Create Workspace"'), true)
  assert.equal(source.includes('aria-label="LLM & API Keys"'), true)
  assert.equal(source.includes('aria-label="User Profile"'), true)

  const userProfileMatches = source.match(/User Profile/g) || []
  assert.equal(userProfileMatches.length >= 1, true)

  assert.equal(source.includes('group-hover:opacity-100 transition-opacity pointer-events-none'), false)
  assert.equal(source.includes('title="Settings"'), false)
  assert.equal(source.includes('title="Search"'), false)
  assert.equal(source.includes('title="Terms & Conditions"'), false)
  assert.equal(source.includes('<CogIcon'), false)
})
