import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses native title tooltips for current navigation actions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('title="New Conversation"'), true)
  assert.equal(source.includes('title="Conversation actions"'), true)
  assert.equal(source.includes('Open conversation tree'), true)
  assert.equal(source.includes('title="Settings"'), true)
  assert.equal(source.includes('title="Profile Settings"'), true)
  assert.equal(source.includes('title="API Keys"'), false)
  assert.equal(source.includes("appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"), true)
})
