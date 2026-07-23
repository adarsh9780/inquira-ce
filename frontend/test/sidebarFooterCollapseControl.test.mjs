import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

test('sidebar collapse control stays in the brand row and the collapsed logo expands it', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf8')
  const brandIndex = source.indexOf('<!-- ─── Brand / Collapse Toggle ─── -->')
  const mainIndex = source.indexOf('<!-- ─── Main Scroll Area ─── -->')

  assert.ok(brandIndex >= 0)
  assert.ok(mainIndex > brandIndex)
  const brandBlock = source.slice(brandIndex, mainIndex)
  assert.match(brandBlock, /@click="uiStore\.isSidebarCollapsed && handleBrandClick\(\)"/)
  assert.match(brandBlock, /@click="handleBrandClick"/)
  assert.match(brandBlock, /ChevronDoubleLeftIcon/)
  assert.doesNotMatch(brandBlock, /ChevronDoubleRightIcon/)
  assert.match(brandBlock, /aria-label="Collapse sidebar"/)
  assert.match(brandBlock, /:aria-label="uiStore\.isSidebarCollapsed \? 'Expand sidebar' : 'Inquira'"/)
})
