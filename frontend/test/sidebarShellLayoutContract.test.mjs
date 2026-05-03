import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app shell owns sidebar rail sizing while UnifiedSidebar fills the provided space', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('class="h-full shrink-0 app-nav-pane"'), true)
  assert.equal(appSource.includes(":class=\"{ 'app-nav-pane-collapsed': appStore.isSidebarCollapsed }\""), true)
  assert.equal(appSource.includes('.app-nav-pane {'), true)
  assert.equal(appSource.includes('width: 260px;'), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(appSource.includes('width: 64px;'), true)

  assert.equal(
    sidebarSource.includes('class="relative z-40 flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden sidebar-root"'),
    true,
  )
  assert.equal(sidebarSource.includes("'w-[260px]'"), false)
  assert.equal(sidebarSource.includes("'w-[64px]'"), false)
  assert.equal(sidebarSource.includes('transition-[width]'), false)
})

test('workspace shell owns pane sizing while child panes stay fluid', () => {
  const panelSource = readFileSync(resolve(process.cwd(), 'src/components/layout/RightPanel.vue'), 'utf-8')
  const leftPaneSource = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue'), 'utf-8')
  const rightPaneSource = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue'), 'utf-8')

  assert.equal(
    panelSource.includes(`class="flex h-full min-w-0 flex-col border-r workspace-center-pane"`),
    true,
  )
  assert.equal(
    panelSource.includes(`:style="{ width: appStore.leftPaneWidth + '%', borderColor: 'var(--color-border)' }"`),
    true,
  )
  assert.equal(
    panelSource.includes(`class="flex h-full min-w-0 flex-col workspace-data-pane"`),
    true,
  )
  assert.equal(
    panelSource.includes(`:style="{ width: rightPaneWidth + '%' }"`),
    true,
  )

  assert.equal(
    leftPaneSource.includes('class="flex h-full w-full min-h-0 min-w-0 flex-col"'),
    true,
  )
  assert.equal(leftPaneSource.includes('leftPaneWidth +'), false)
  assert.equal(leftPaneSource.includes('class="flex h-full flex-col"'), false)

  assert.equal(
    rightPaneSource.includes('class="flex h-full w-full min-h-0 min-w-0 flex-col"'),
    true,
  )
  assert.equal(rightPaneSource.includes('rightPaneWidth +'), false)
  assert.equal(rightPaneSource.includes('class="flex h-full flex-col"'), false)
})
