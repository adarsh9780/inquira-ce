import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar rail uses native title tooltips for modern navigation actions', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(sidebarSource.includes('title="Create Workspace"'), true)
  assert.equal(sidebarSource.includes('title="Datasets"'), true)
  assert.equal(sidebarSource.includes('title="Conversations"'), true)
  assert.equal(sidebarSource.includes('title="Schema Editor"'), true)
  assert.equal(sidebarSource.includes('title="LLM & API Keys"'), true)
  assert.equal(sidebarSource.includes('title="User Profile"'), true)

  assert.equal(
    sidebarSource.includes('group-hover:opacity-100 transition-opacity pointer-events-none'),
    false,
  )
})
