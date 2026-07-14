import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

test('sidebar expand and collapse control sits immediately above Settings', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf8')
  const toggleIndex = source.indexOf('<!-- Sidebar collapse / expand -->')
  const settingsIndex = source.indexOf('<!-- Settings -->')

  assert.ok(toggleIndex >= 0)
  assert.ok(settingsIndex > toggleIndex)
  assert.match(source.slice(toggleIndex, settingsIndex), /@click="handleBrandClick"/)
  assert.match(source.slice(toggleIndex, settingsIndex), /ChevronDoubleRightIcon/)
  assert.match(source.slice(toggleIndex, settingsIndex), /ChevronDoubleLeftIcon/)
  assert.match(source.slice(toggleIndex, settingsIndex), /:aria-label="appStore\.isSidebarCollapsed \? 'Expand sidebar' : 'Collapse sidebar'"/)
})
