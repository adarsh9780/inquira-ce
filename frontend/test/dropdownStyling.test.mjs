import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('results uses a direct category control with contextual artifact dropdowns', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')
  const dropdownPath = resolve(process.cwd(), 'src/components/ui/HeaderDropdown.vue')

  const figureTab = readFileSync(figureTabPath, 'utf-8')
  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const rightPane = readFileSync(rightPanePath, 'utf-8')
  const dropdown = readFileSync(dropdownPath, 'utf-8')

  assert.equal(rightPane.includes('<SegmentedControl'), true)
  assert.equal(rightPane.includes('<HeaderDropdown'), false)
  assert.equal(rightPane.includes('v-model="selectedCategory"'), true)
  assert.equal(rightPane.includes('aria-label="Result views"'), true)
  assert.equal(rightPane.includes("{ value: 'table', label: 'Tables', icon: TableCellsIcon, count: tableResultCount.value }"), true)
  assert.equal(rightPane.includes("{ value: 'chart', label: 'Charts', icon: ChartBarIcon, count: chartResultCount.value }"), true)
  assert.equal(rightPane.includes("{ value: 'runs', label: 'Runs', icon: PlayCircleIcon, count: runResultCount.value }"), true)
  assert.equal(figureTab.includes('<HeaderDropdown'), true)
  assert.equal(tableTab.includes('<HeaderDropdown'), true)
  assert.equal(figureTab.includes('<select'), false)
  assert.equal(tableTab.includes('<select'), false)
  assert.equal(rightPane.includes('max-width-class="w-[9.5rem]"'), false)
  assert.equal(dropdown.includes('data-header-dropdown-icon'), true)
  assert.equal(dropdown.includes('const maxLabelChars = computed(() => Math.max('), true)
  assert.equal(dropdown.includes('width: `${widthChars}ch`'), true)
  assert.equal(dropdown.includes("maxWidth: '100%'"), true)
  assert.equal(dropdown.includes('text-[13px] font-medium'), true)
  assert.equal(dropdown.includes('ComboboxTrigger'), true)
  assert.equal(dropdown.includes('ComboboxPortal'), true)
  assert.equal(dropdown.includes('dropdownSurfaceClass'), true)
  assert.equal(dropdown.includes('updateFloatingDropdownPosition'), false)
  assert.equal(dropdown.includes('position="popper"'), true)
  assert.equal(dropdown.includes("width: 'var(--reka-combobox-trigger-width)'"), true)
  assert.equal(dropdown.includes('triggerLabel'), true)
  assert.equal(dropdown.includes('dropdownMinWidth'), true)
})
