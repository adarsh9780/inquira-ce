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
  assert.equal(panelSource.includes('v-if="appStore.showLeftPane"'), true)
  assert.equal(panelSource.includes('v-if="appStore.showRightPane"'), true)
  assert.equal(panelSource.includes('const leftPaneWidth = computed(() => appStore.showRightPane ? appStore.leftPaneWidth : 100)'), true)
  assert.equal(panelSource.includes('const rightPaneWidth = computed(() => appStore.showLeftPane ? (100 - appStore.leftPaneWidth) : 100)'), true)
  assert.equal(panelSource.includes(':style="{ width: rightPaneWidth + \'%\' }"'), true)
})

test('sidebar keeps the current animated text-collapse and scroll layout', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('activeWorkspaceName'), true)
  assert.equal(sidebarSource.includes('class="flex min-h-0 flex-1 flex-col overflow-x-hidden px-2 custom-scrollbar"'), true)
  assert.equal(sidebarSource.includes('class="group relative flex items-center rounded-lg cursor-pointer transition-colors hover:bg-[var(--color-text-main)]/5"'), true)
  assert.equal(sidebarSource.includes('<Transition name="sidebar-section">'), false)
})

test('sidebar icons keep fixed sizing during collapse/expand', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('h-6 w-6 shrink-0 items-center justify-center'), true)
  assert.equal(sidebarSource.includes('KeyIcon class="h-5 w-5"'), true)
  assert.equal(sidebarSource.includes('sidebar-initials-avatar'), true)
  assert.equal(sidebarSource.includes('class="h-14 shrink-0 border-b border-[var(--color-border)] flex items-center pl-[20px] pr-4"'), true)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'workspace' ? 'scale-110' : ''"), false)
  assert.equal(sidebarSource.includes("appStore.activeTab === 'schema-editor' ? 'scale-110' : ''"), false)
})
