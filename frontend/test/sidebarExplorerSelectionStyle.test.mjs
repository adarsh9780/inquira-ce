import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar renders dropdown-driven explorer style with compact emerald active highlights', () => {
  const unifiedSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )
  const datasetsSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'),
    'utf-8',
  )
  const conversationsSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversations.vue'),
    'utf-8',
  )

  assert.equal(unifiedSource.includes('Workspace explorer'), true)
  assert.equal(datasetsSource.includes("bg-emerald-50 text-emerald-800 border-emerald-200"), true)
  assert.equal(conversationsSource.includes("bg-emerald-50 text-emerald-800 border-emerald-200"), true)
  assert.equal(datasetsSource.includes('ChevronRightIcon'), true)
  assert.equal(conversationsSource.includes('ChevronRightIcon'), true)
  assert.equal(datasetsSource.includes('text-[11px] uppercase tracking'), true)
  assert.equal(conversationsSource.includes('text-[11px] uppercase tracking'), true)
})
