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
  assert.equal(sidebarSource.includes("expandSidebarFromIcon('datasets')"), true)
  assert.equal(sidebarSource.includes("expandSidebarFromIcon('conversations')"), true)
  assert.equal(sidebarSource.includes("expandSidebarFromIcon('settings')"), false)
})

test('sidebar keeps logo mounted and uses width transition to avoid layout jerk', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('transition: width var(--motion-duration-standard) var(--motion-ease-standard);'), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(sidebarSource.includes('class="sidebar-brand-shell h-14 shrink-0 border-b"'), true)
  assert.equal(sidebarSource.includes('<img :src="logo" alt="Inquira" class="h-8 w-8 rounded-lg shadow-sm" />'), true)
  assert.equal(sidebarSource.includes('sidebar-brand-wordmark-collapsed'), true)
  assert.equal(sidebarSource.includes('sidebar-brand-wordmark-expanded'), true)
})
