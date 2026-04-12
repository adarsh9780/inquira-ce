import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app uses a collapsed icon rail to reopen sidebar without losing left-edge affordance', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(appSource.includes('function toggleSidebarVisibility() {'), true)
  assert.equal(appSource.includes('v-if="!appStore.isSidebarCollapsed"'), true)
  assert.equal(appSource.includes('v-if="appStore.isSidebarCollapsed"'), true)
  assert.equal(appSource.includes('class="app-sidebar-rail"'), true)
  assert.equal(appSource.includes('@mouseenter="expandSidebarFromRail()"'), true)
  assert.equal(appSource.includes("title=\"Open datasets sidebar\""), true)
  assert.equal(appSource.includes("title=\"Open conversations sidebar\""), true)
  assert.equal(appSource.includes("title=\"Open settings sidebar\""), true)
  assert.equal(appSource.includes('CircleStackIcon'), true)
  assert.equal(appSource.includes('ChatBubbleLeftRightIcon'), true)
  assert.equal(appSource.includes('Cog6ToothIcon'), true)
  assert.equal(appSource.includes('<StatusBar />'), true)
  assert.equal(appSource.includes('<Transition name="sidebar-shell">'), true)
  assert.equal(appSource.includes('<Transition name="sidebar-rail-shell">'), true)
  assert.equal(appSource.includes('.sidebar-shell-enter-active'), true)
})
