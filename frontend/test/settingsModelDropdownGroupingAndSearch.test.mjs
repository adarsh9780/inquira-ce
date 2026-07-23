import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings model selectors use searchable HeaderDropdown controls', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/LLMSettingsTab.vue')
  const source = readFileSync(tabPath, 'utf-8')

  const searchableUsages = source.match(/:searchable="true"/g) ?? []

  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes(':backend-search="searchProviderModels"'), true)
  assert.equal(searchableUsages.length >= 2, true)
  assert.equal(source.includes('search-placeholder="Search model"'), true)
})

test('shared model dropdown supports provider grouping and search filtering', () => {
  const headerDropdownPath = resolve(process.cwd(), 'src/components/ui/HeaderDropdown.vue')
  const sharedDropdownPath = resolve(process.cwd(), 'src/components/ui/dropdownShared.js')
  const headerSource = readFileSync(headerDropdownPath, 'utf-8')
  const sharedSource = readFileSync(sharedDropdownPath, 'utf-8')

  assert.equal(headerSource.includes('groupByProvider'), true)
  assert.equal(headerSource.includes('groupedFilteredOptions'), true)
  assert.equal(headerSource.includes('searchQuery'), true)
  assert.equal(headerSource.includes("default: 'Search models'"), true)
  assert.equal(headerSource.includes("default: 'No results found'"), true)
  assert.equal(headerSource.includes('sharedProviderLabel'), true)
  assert.equal(headerSource.includes('dropdownSearchRowClass'), true)

  assert.equal(sharedSource.includes('sticky top-0 z-10'), true)
})
