import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('collapsed sidebar expands only on explicit click and not on hover', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('@mouseenter='), false)
  assert.equal(appSource.includes('@mouseleave='), false)
  assert.equal(sidebarSource.includes('@mouseenter='), false)
  assert.equal(sidebarSource.includes('@mouseleave='), false)
  assert.equal(sidebarSource.includes('@click="handleBrandClick"'), true)
  assert.equal(sidebarSource.includes('function openWorkspaceRail(target = \'\') {'), false)
  assert.equal(sidebarSource.includes('title="New Conversation"'), true)
  assert.equal(sidebarSource.includes('title="API Keys"'), true)
})

test('sidebar branding keeps a stable fixed top row while the shell owns width animation', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(appSource.includes('transition: width var(--motion-duration-standard) var(--motion-ease-standard);'), true)
  assert.equal(appSource.includes('.app-nav-pane-collapsed {'), true)
  assert.equal(sidebarSource.includes('class="h-14 shrink-0 border-b border-[var(--color-border)] flex items-center pl-[20px] pr-4"'), true)
  assert.equal(sidebarSource.includes('class="flex h-full w-full items-center transition-opacity hover:opacity-70 focus:outline-none"'), true)
  assert.equal(sidebarSource.includes('alt="Inquira"'), true)
})
