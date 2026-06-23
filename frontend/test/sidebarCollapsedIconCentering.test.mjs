import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('collapsed sidebar relies on app-shell width and visually hidden label copy', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('width: 64px;'), true)
  assert.equal(sidebarSource.includes("max-w-0 opacity-0 ml-0"), true)
  assert.equal(sidebarSource.includes("'max-w-[176px] opacity-100 ml-2.5'"), true)
})

test('collapsed sidebar rows keep centered fixed-size icon containers', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  const justifyCenterCount = (sidebarSource.match(/justify-center px-0/g) || []).length
  assert.ok(justifyCenterCount >= 3)
  assert.ok(sidebarSource.includes('.sidebar-row-icon'))
  assert.ok(sidebarSource.includes('height: 1.5rem;'))
  assert.ok(sidebarSource.includes('width: 1.5rem;'))
  assert.ok(sidebarSource.includes("appStore.isSidebarCollapsed ? 'justify-center px-0'"))
})

test('conversation ellipsis menu is restored on the sidebar conversation list', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes("appStore.isSidebarCollapsed ? 'hidden' :"), false)
  assert.equal(sidebarSource.includes('data-conversation-actions-menu'), true)
  assert.equal(sidebarSource.includes('EllipsisHorizontalIcon'), true)
})
