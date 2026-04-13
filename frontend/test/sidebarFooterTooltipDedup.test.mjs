import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar footer uses native title tooltips and keeps a single settings icon entry', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  assert.equal(source.includes('title="Create Workspace"'), true)
  assert.equal(source.includes('title="Settings"'), true)
  assert.equal(source.includes('title="Search"'), true)
  assert.equal(source.includes('title="Terms & Conditions"'), true)

  assert.equal(source.includes('aria-label="Create Workspace"'), true)
  assert.equal(source.includes('aria-label="Settings"'), true)
  assert.equal(source.includes('aria-label="Search"'), true)
  assert.equal(source.includes('aria-label="Terms & Conditions"'), true)

  const cogIconMatches = source.match(/<CogIcon\b/g) || []
  assert.equal(cogIconMatches.length, 1)

  assert.equal(source.includes('group-hover:opacity-100 transition-opacity pointer-events-none'), false)
  assert.equal(source.includes("expandSidebarFromIcon('settings')"), false)
})
