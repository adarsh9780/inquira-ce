import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('right panel animates terminal open and close via height and opacity transitions', () => {
  const panelSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/RightPanel.vue'),
    'utf-8',
  )

  assert.equal(panelSource.includes('const terminalVisualHeight = computed(() => {'), true)
  assert.equal(panelSource.includes('const workspaceVisualHeight = computed(() => 100 - terminalVisualHeight.value)'), true)
  assert.equal(panelSource.includes('transition-[height] duration-300'), true)
  assert.equal(panelSource.includes('transition-[height,opacity,border-color] duration-300'), true)
  assert.equal(panelSource.includes('h-0 opacity-0 pointer-events-none'), true)
  assert.equal(panelSource.includes('v-show="appStore.isTerminalOpen && appStore.activeTab === \'workspace\'"'), false)
  assert.equal(panelSource.includes('v-if="!appStore.isDataFocusMode"'), true)
  assert.equal(panelSource.includes('const rightPaneWidth = computed(() => appStore.isDataFocusMode ? 100 : (100 - appStore.leftPaneWidth))'), true)
  assert.equal(panelSource.includes(':style="{ width: rightPaneWidth + \'%\' }"'), true)
})

test('sidebar and explorer sections use animated collapse transitions', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )
  const workspacesSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue'),
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

  assert.equal(sidebarSource.includes('<Transition name="sidebar-section">'), true)
  assert.equal(sidebarSource.includes(':is-collapsed="false"'), true)
  assert.equal(sidebarSource.includes('<Transition name="sidebar-brand">'), false)
  assert.equal(sidebarSource.includes('.sidebar-section-enter-active'), true)
  assert.equal(workspacesSource.includes('transition name="workspace-dropdown"'), true)
  assert.equal(datasetsSource.includes('<Transition name="sidebar-list">'), true)
  assert.equal(conversationsSource.includes('<Transition name="sidebar-list">'), true)
  assert.equal(workspacesSource.includes('.workspace-dropdown-enter-active'), true)
  assert.equal(datasetsSource.includes('.sidebar-list-enter-active'), true)
  assert.equal(conversationsSource.includes('.sidebar-list-enter-active'), true)
})

test('sidebar icons keep fixed size to avoid toggle jitter', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )
  const workspacesSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue'),
    'utf-8',
  )

  assert.equal(workspacesSource.includes('BuildingOffice2Icon class="w-3.5 h-3.5 shrink-0"'), true)
  assert.equal(workspacesSource.includes('scale-110'), false)
  // Workspace/Schema tabs moved to status bar; sidebar now has Settings, Terms, Logout
  assert.equal(sidebarSource.includes("CogIcon class=\"w-4 h-4 shrink-0\""), true)
  assert.equal(sidebarSource.includes("DocumentIcon class=\"w-4 h-4 shrink-0\""), true)
  assert.equal(sidebarSource.includes("ArrowRightOnRectangleIcon class=\"w-4 h-4 shrink-0\""), true)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'workspace' ? 'scale-110' : ''"), false)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'schema-editor' ? 'scale-110' : ''"), false)
})
