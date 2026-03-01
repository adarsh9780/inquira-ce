import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses dedicated collapse toggle button and keeps collapsed quick summaries', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  assert.equal(source.includes('function toggleSidebar() {'), true)
  assert.equal(source.includes('@click="toggleSidebar"'), true)
  assert.equal(source.includes('Expand sidebar'), true)
  assert.equal(source.includes('Collapse sidebar'), true)
  assert.equal(source.includes("v-if=\"appStore.isSidebarCollapsed\""), true)
  assert.equal(source.includes('Kernel'), true)
  assert.equal(source.includes('Workspace'), true)
  assert.equal(source.includes('Dataset'), true)
})
