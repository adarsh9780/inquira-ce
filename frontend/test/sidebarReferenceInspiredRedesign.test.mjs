import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar keeps compact workspace hierarchy while creation lives in the context bar', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('PencilSquareIcon'), false)
  assert.equal(source.includes('class="sidebar-nav-row sidebar-primary-row'), false)
  assert.equal(source.includes('No conversations yet'), true)
  assert.equal(source.includes('MagnifyingGlassIcon'), false)
  assert.equal(source.includes('Search conversations'), false)
  assert.equal(source.includes('filteredSidebarWorkspaces'), true)
  assert.equal(source.includes('workspaceMatchesSidebarSearch'), false)
  assert.equal(source.includes('sidebarSearchOpen'), false)
  assert.equal(source.includes('visibleConversationsForSidebar(workspace)'), true)
  assert.equal(source.includes('.sidebar-nav-row'), true)
  assert.equal(source.includes('.sidebar-section-label'), true)
  assert.equal(source.includes('class="mt-2 space-y-2"'), true)
  assert.equal(source.includes('class="space-y-px pl-6 pr-1"'), true)
  assert.equal(source.includes('text-[18px] font-normal leading-none'), false)
  assert.equal(source.includes('Datasets and column metadata'), false)
  assert.equal(source.includes('Turns across this workspace'), false)
})
