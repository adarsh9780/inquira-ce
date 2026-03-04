import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app uses binary sidebar visibility mode with an external show-sidebar handle', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(appSource.includes('function toggleSidebarVisibility() {'), true)
  assert.equal(appSource.includes('v-if="!appStore.isSidebarCollapsed"'), true)
  assert.equal(appSource.includes('v-if="appStore.isSidebarCollapsed"'), true)
  assert.equal(appSource.includes('title="Show sidebar"'), true)
  assert.equal(appSource.includes('aria-label="Show sidebar"'), true)
  assert.equal(appSource.includes('<Transition name="sidebar-shell">'), true)
  assert.equal(appSource.includes('.sidebar-shell-enter-active'), true)
})
