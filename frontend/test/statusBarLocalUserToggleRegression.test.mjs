import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('local user button in status bar uses true sidebar toggle behavior', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )

  assert.equal(statusBarSource.includes('@click.stop="toggleSidebarFromStatusBar"'), true)
  assert.equal(statusBarSource.includes('function toggleSidebarFromStatusBar() {'), true)
  assert.equal(statusBarSource.includes('appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)'), true)
  assert.equal(statusBarSource.includes('function openSidebar() {'), false)
})
