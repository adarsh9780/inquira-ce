import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar keeps active workspace in root row and hides it from workspace list', () => {
  const unifiedPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const workspacesPath = resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue')
  const unifiedSource = readFileSync(unifiedPath, 'utf-8')
  const workspacesSource = readFileSync(workspacesPath, 'utf-8')

  assert.equal(unifiedSource.includes('CheckCircleIcon'), true)
  assert.equal(unifiedSource.includes('activeWorkspaceName'), true)
  assert.equal(unifiedSource.includes('v-else-if="!appStore.isSidebarCollapsed"'), true)
  assert.equal(workspacesSource.includes('const visibleWorkspaces = computed(() => {'), true)
  assert.equal(workspacesSource.includes('ws.id !== activeId'), true)
  assert.equal(workspacesSource.includes('v-for="ws in visibleWorkspaces"'), true)
})
