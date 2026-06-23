import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar renders minimal explorer style with compact brand active highlights', () => {
  const unifiedSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )
  const datasetsSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'),
    'utf-8',
  )

  assert.equal(unifiedSource.includes('Workspace explorer'), false)
  assert.equal(datasetsSource.includes("bg-[var(--color-accent-soft)] text-[var(--color-accent)]"), true)
  assert.equal(unifiedSource.includes("appStore.activeConversationId === conv.id ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)]'"), true)
  assert.equal(unifiedSource.includes('sidebar-workspace-row-active'), true)
  assert.equal(datasetsSource.includes("bg-emerald-50 text-emerald-800"), false)
  assert.equal(unifiedSource.includes("bg-emerald-50 text-emerald-800"), false)
  assert.equal(datasetsSource.includes('ChevronRightIcon'), true)
  assert.equal(datasetsSource.includes('text-[11px] uppercase tracking'), true)
  assert.equal(unifiedSource.includes('text-[18px] font-normal leading-none'), false)
  assert.equal(unifiedSource.includes('.sidebar-section-label'), true)
})
