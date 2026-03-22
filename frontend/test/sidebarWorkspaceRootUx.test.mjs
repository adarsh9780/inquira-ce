import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses a single-select workspace dropdown above the explorer sections', () => {
  const unifiedPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const workspacesPath = resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue')
  const unifiedSource = readFileSync(unifiedPath, 'utf-8')
  const workspacesSource = readFileSync(workspacesPath, 'utf-8')

  assert.equal(unifiedSource.includes('Workspace explorer'), true)
  assert.equal(unifiedSource.includes('Pick one workspace, then browse its datasets and conversations.'), true)
  assert.equal(workspacesSource.includes('ListboxButton'), true)
  assert.equal(workspacesSource.includes('ListboxOptions'), true)
  assert.equal(workspacesSource.includes('Selected workspace'), true)
  assert.equal(workspacesSource.includes('ChevronUpDownIcon'), true)
  assert.equal(workspacesSource.includes('appStore.workspaces'), true)
})
