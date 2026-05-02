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
  assert.equal(panelSource.includes('transition-[height] motion-slow'), true)
  assert.equal(panelSource.includes('transition-[height,opacity,border-color] motion-slow'), true)
  assert.equal(panelSource.includes('h-0 pointer-events-none opacity-0'), true)
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
  // Current redesign keeps a single top content area and fixed bottom stack
  assert.equal(sidebarSource.includes('activeWorkspaceName'), true)
  assert.equal(sidebarSource.includes('sidebar-workspace-row'), true)
  assert.equal(sidebarSource.includes('custom-scrollbar flex-1 overflow-y-auto overflow-x-hidden'), true)
  assert.equal(sidebarSource.includes('sidebar-conversation-row'), true)
  // No old transition patterns
  assert.equal(sidebarSource.includes('<Transition name="sidebar-section">'), false)
  assert.equal(sidebarSource.includes('<Transition name="sidebar-brand">'), false)
  assert.equal(sidebarSource.includes('.sidebar-section-enter-active'), false)
})

test('sidebar icons keep fixed size to avoid toggle jitter', () => {
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )
  // New design uses shrink-0 on icons
  assert.equal(sidebarSource.includes('Bars3Icon class="h-4 w-4 shrink-0"'), true)
  assert.equal(sidebarSource.includes('FolderPlusIcon class="h-4 w-4 shrink-0"'), true)
  assert.equal(sidebarSource.includes('KeyIcon class="h-4 w-4 shrink-0"'), true)
  assert.equal(sidebarSource.includes('class="sidebar-brand-shell shrink-0 border-b"'), true)
  assert.equal(sidebarSource.includes('.sidebar-brand-stack {'), true)
  assert.equal(sidebarSource.includes('width: var(--size-sidebar-brand-rail);'), true)
  assert.equal(sidebarSource.includes('min-width: var(--size-sidebar-brand-rail);'), true)
  assert.equal(sidebarSource.includes('sidebar-brand-copy'), false)
  // No scale animations on workspace/schema tabs
  assert.equal(sidebarSource.includes("appStore.activeTab === 'workspace' ? 'scale-110' : ''"), false)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'schema-editor' ? 'scale-110' : ''"), false)
  // CE: logout icon removed
  assert.equal(sidebarSource.includes("ArrowRightOnRectangleIcon"), false)
})
