import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar renders workspace-root explorer style with compact green active highlights', () => {
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

  assert.equal(unifiedSource.includes('CheckCircleIcon'), true)
  assert.equal(unifiedSource.includes('const activeWorkspaceName = computed(() => {'), true)
  assert.equal(datasetsSource.includes("bg-green-50/50 text-green-700"), true)
  assert.equal(conversationsSource.includes("bg-green-50/50 text-green-700"), true)
  assert.equal(datasetsSource.includes('text-[11px] uppercase tracking'), true)
  assert.equal(conversationsSource.includes('text-[11px] uppercase tracking'), true)
})
