import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table and figure headers use shared HeaderDropdown control instead of native select', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const dropdownPath = resolve(process.cwd(), 'src/components/ui/HeaderDropdown.vue')

  const figureTab = readFileSync(figureTabPath, 'utf-8')
  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const dropdown = readFileSync(dropdownPath, 'utf-8')

  assert.equal(figureTab.includes('<HeaderDropdown'), true)
  assert.equal(tableTab.includes('<HeaderDropdown'), true)
  assert.equal(figureTab.includes('<select'), false)
  assert.equal(tableTab.includes('<select'), false)
  assert.equal(dropdown.includes('text-[13px] font-medium'), true)
  assert.equal(dropdown.includes('ListboxButton'), true)
})
