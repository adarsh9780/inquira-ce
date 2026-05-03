import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('collapsed sidebar relies on app-shell width and visually hidden label copy', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('width: 64px;'), true)
  assert.equal(sidebarSource.includes("max-w-0 opacity-0 ml-0"), true)
  assert.equal(sidebarSource.includes("'max-w-[200px] opacity-100 ml-3'"), true)
})

test('collapsed sidebar rows keep centered fixed-size icon containers', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  const justifyCenterCount = (sidebarSource.match(/justify-center px-0/g) || []).length
  assert.ok(justifyCenterCount >= 3)
  assert.ok(sidebarSource.includes('h-6 w-6 shrink-0 items-center justify-center'))
  assert.ok(sidebarSource.includes("appStore.isSidebarCollapsed ? 'justify-center px-0'"))
})

test('conversation ellipsis menu renders only when the sidebar is expanded', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes("appStore.isSidebarCollapsed ? 'hidden' :"), false)
  assert.equal(sidebarSource.includes('v-if="!appStore.isSidebarCollapsed"'), true)
  assert.equal(sidebarSource.includes('data-conversation-actions-menu'), true)
})
