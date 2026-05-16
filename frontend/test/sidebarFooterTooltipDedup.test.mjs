import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar footer uses settings, collapse, and profile entry points', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('title="Settings"'), true)
  assert.equal(source.includes('title="Profile Settings"'), true)
  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"), true)
  assert.equal(source.includes('title="API Keys"'), false)
  assert.equal(source.includes('title="Search"'), false)
  assert.equal(source.includes('title="Terms & Conditions"'), false)
  assert.equal(source.includes('<Cog6ToothIcon'), true)
})
