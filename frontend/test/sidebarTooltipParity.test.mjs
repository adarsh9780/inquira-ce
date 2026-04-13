import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar top and footer icons both use native title tooltips', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(sidebarSource.includes('title="Open datasets sidebar"'), true)
  assert.equal(sidebarSource.includes('title="Open conversations sidebar"'), true)
  assert.equal(sidebarSource.includes('title="Open schema editor"'), true)

  assert.equal(sidebarSource.includes('title="Create Workspace"'), true)
  assert.equal(sidebarSource.includes('title="Settings"'), true)
  assert.equal(sidebarSource.includes('title="Search"'), true)
  assert.equal(sidebarSource.includes('title="Terms & Conditions"'), true)

  assert.equal(
    sidebarSource.includes('group-hover:opacity-100 transition-opacity pointer-events-none'),
    false,
  )
})
