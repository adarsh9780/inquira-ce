import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app uses binary sidebar visibility mode and delegates reopening control to status bar', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(appSource.includes('function toggleSidebarVisibility() {'), true)
  assert.equal(appSource.includes('v-if="!appStore.isSidebarCollapsed"'), true)
  assert.equal(appSource.includes('v-if="appStore.isSidebarCollapsed"'), false)
  assert.equal(appSource.includes('title="Show sidebar"'), false)
  assert.equal(appSource.includes('aria-label="Show sidebar"'), false)
  assert.equal(appSource.includes('<StatusBar />'), true)
  assert.equal(appSource.includes('<Transition name="sidebar-shell">'), true)
  assert.equal(appSource.includes('.sidebar-shell-enter-active'), true)
})
