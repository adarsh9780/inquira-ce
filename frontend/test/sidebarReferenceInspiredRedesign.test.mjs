import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar redesign keeps quick actions, search filtering, and compact hierarchy', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('PencilSquareIcon'), true)
  assert.equal(source.includes('MagnifyingGlassIcon'), true)
  assert.equal(source.includes('Search conversations'), true)
  assert.equal(source.includes('filteredSidebarWorkspaces'), true)
  assert.equal(source.includes('workspaceMatchesSidebarSearch'), true)
  assert.equal(source.includes('visibleConversationsForSidebar(workspace)'), true)
  assert.equal(source.includes('.sidebar-nav-row'), true)
  assert.equal(source.includes('.sidebar-section-label'), true)
  assert.equal(source.includes('text-[18px] font-normal leading-none'), false)
  assert.equal(source.includes('Datasets and column metadata'), false)
  assert.equal(source.includes('Turns across this workspace'), false)
})
