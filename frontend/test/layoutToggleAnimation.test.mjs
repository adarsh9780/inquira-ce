import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('right panel animates terminal open and close via height and opacity transitions', () => {
  const panelSource = readFileSync(resolve(process.cwd(), 'src/components/layout/RightPanel.vue'), 'utf-8')

  assert.equal(panelSource.includes('const terminalVisualHeight = computed(() => {'), true)
  assert.equal(panelSource.includes('const workspaceVisualHeight = computed(() => 100 - terminalVisualHeight.value)'), true)
  assert.equal(panelSource.includes('transition-[height] motion-slow'), true)
  assert.equal(panelSource.includes('transition-[height,opacity,border-color] motion-slow'), true)
  assert.equal(panelSource.includes('h-0 pointer-events-none opacity-0'), true)
  assert.equal(panelSource.includes('v-if="appStore.showLeftPane"'), false)
  assert.equal(panelSource.includes(':aria-hidden="!appStore.showRightPane"'), false)
  assert.equal(panelSource.includes('workspace-data-pane-hidden'), false)
  assert.equal(panelSource.includes('const leftPaneWidth = computed(() => appStore.leftPaneWidth)'), true)
  assert.equal(panelSource.includes('const rightPaneWidth = computed(() => 100 - appStore.leftPaneWidth)'), true)
  assert.equal(panelSource.includes('width: `${rightPaneWidth}%`'), true)
})

test('sidebar keeps the current animated text-collapse and scroll layout', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const menuSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversationActionsMenu.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('workspaceRuntimeLabel'), false)
  assert.equal(sidebarSource.includes('class="flex min-h-0 flex-1 flex-col overflow-hidden px-2"'), true)
  assert.equal(sidebarSource.includes('class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-1 custom-scrollbar"'), true)
  assert.equal(sidebarSource.includes('<SidebarConversations'), false)
  assert.equal(menuSource.includes('data-conversation-actions-menu'), true)
  assert.equal(sidebarSource.includes('<Transition name="sidebar-section">'), false)
})

test('sidebar icons keep fixed sizing during collapse/expand', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(sidebarSource.includes('.sidebar-row-icon'), true)
  assert.equal(styleSource.includes('--size-sidebar-inline-icon: 1rem;'), true)
  assert.equal(sidebarSource.includes('height: calc(var(--size-sidebar-inline-icon) + 0.5rem);'), true)
  assert.equal(sidebarSource.includes('width: calc(var(--size-sidebar-inline-icon) + 0.5rem);'), true)
  assert.equal(sidebarSource.includes('.sidebar-row-icon :deep(svg)'), true)
  assert.equal(sidebarSource.includes('Cog6ToothIcon class="h-5 w-5"'), true)
  assert.equal(sidebarSource.includes('ChevronDoubleRightIcon'), false)
  assert.equal(sidebarSource.includes('ChevronDoubleLeftIcon class="h-4 w-4"'), true)
  assert.equal(sidebarSource.includes('sidebar-initials-avatar'), true)
  assert.equal(sidebarSource.includes('class="sidebar-brand-row justify-between px-4"'), true)
  assert.equal(sidebarSource.includes('transition: all var(--motion-duration-slow) var(--motion-ease-emphasized)'), false)
  assert.equal(sidebarSource.includes('will-change: max-width, opacity, margin-left;'), true)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'workspace' ? 'scale-110' : ''"), false)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'schema-editor' ? 'scale-110' : ''"), false)
})
