import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar nests collapsible datasets and conversations under the selected workspace', () => {
  const unifiedSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  // Unified sidebar has datasets and conversations sections inline
  // No separate SidebarDatasets or SidebarConversations components
  assert.equal(unifiedSource.includes('SidebarDatasets'), false)
  assert.equal(unifiedSource.includes('SidebarConversations'), false)
  
  // Workspace check still present
  assert.equal(unifiedSource.includes('appStore.hasWorkspace'), true)
  
  // Expansion state refs exist for workspaces, datasets, conversations
  assert.equal(unifiedSource.includes('const workspacesExpanded = ref(true)'), true)
  assert.equal(unifiedSource.includes('const datasetsExpanded = ref(true)'), true)
  assert.equal(unifiedSource.includes('const conversationsExpanded = ref(true)'), true)
  
  // Only outer workspace uses folder open/closed icon state
  assert.equal(unifiedSource.includes('FolderOpenIcon v-if="workspacesExpanded"'), true)
  assert.equal(unifiedSource.includes('FolderOpenIcon v-if="datasetsExpanded"'), false)
  assert.equal(unifiedSource.includes('FolderOpenIcon v-if="conversationsExpanded"'), false)
  assert.equal(unifiedSource.includes("v-if=\"appStore.hasWorkspace && workspacesExpanded\""), true)
})
