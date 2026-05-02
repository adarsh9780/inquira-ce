import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('collapsed sidebar expands only on explicit icon click (never on hover)', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('@mouseenter='), false)
  assert.equal(appSource.includes('@mouseleave='), false)
  assert.equal(sidebarSource.includes('@mouseenter='), false)
  assert.equal(sidebarSource.includes('@mouseleave='), false)
  assert.equal(sidebarSource.includes('class="sidebar-rail-btn"'), true)
  assert.equal(sidebarSource.includes('function openWorkspaceRail(target = \'\') {'), false)
  assert.equal(sidebarSource.includes("title=\"Open workspace settings\""), true)
  assert.equal(sidebarSource.includes("title=\"New Conversation\""), true)
  assert.equal(sidebarSource.includes("title=\"LLM & API Keys\""), true)
})

test('sidebar keeps a fixed top rail and uses width transition to avoid layout jerk', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('transition: width var(--motion-duration-standard) var(--motion-ease-standard);'), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(sidebarSource.includes('class="sidebar-brand-shell shrink-0 border-b"'), true)
  assert.equal(sidebarSource.includes('sidebar-brand-stack'), true)
  assert.equal(sidebarSource.includes('sidebar-brand-logo-shell'), true)
  assert.equal(sidebarSource.includes('Bars3Icon class="h-4 w-4 shrink-0"'), true)
  assert.equal(sidebarSource.includes('Inquira logo'), true)
  assert.equal(sidebarSource.includes('sidebar-brand-copy'), false)
})
