import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('unified results header owns the shared HeaderDropdown instead of renderer-specific selects', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')
  const dropdownPath = resolve(process.cwd(), 'src/components/ui/HeaderDropdown.vue')

  const figureTab = readFileSync(figureTabPath, 'utf-8')
  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const rightPane = readFileSync(rightPanePath, 'utf-8')
  const dropdown = readFileSync(dropdownPath, 'utf-8')

  assert.equal(rightPane.includes('<HeaderDropdown'), true)
  assert.equal(rightPane.includes('v-model="selectedResultId"'), true)
  assert.equal(rightPane.includes('aria-label="Select result"'), true)
  assert.equal(figureTab.includes('<HeaderDropdown'), false)
  assert.equal(tableTab.includes('<HeaderDropdown'), false)
  assert.equal(figureTab.includes('<select'), false)
  assert.equal(tableTab.includes('<select'), false)
  assert.equal(rightPane.includes('max-width-class="w-[clamp(11rem,28vw,20rem)]"'), true)
  assert.equal(dropdown.includes('const maxLabelChars = computed(() => {'), true)
  assert.equal(dropdown.includes('width: `${widthChars}ch`'), true)
  assert.equal(dropdown.includes("maxWidth: '100%'"), true)
  assert.equal(dropdown.includes('text-[13px] font-medium'), true)
  assert.equal(dropdown.includes('ListboxButton'), true)
  assert.equal(dropdown.includes('Portal'), true)
  assert.equal(dropdown.includes('dropdownSurfaceClass'), true)
  assert.equal(dropdown.includes('updateFloatingDropdownPosition'), true)
  assert.equal(dropdown.includes('updateFloatingPosition'), true)
})
