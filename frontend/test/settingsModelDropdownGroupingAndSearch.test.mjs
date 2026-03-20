import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings model selectors are grouped by provider and searchable', () => {
  const apiTabPath = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(apiTabPath, 'utf-8')

  const groupedUsages = source.match(/:group-by-provider="true"/g) ?? []
  const searchableUsages = source.match(/:searchable="true"/g) ?? []
  const searchPlaceholderUsages = source.match(/search-placeholder="Search models"/g) ?? []

  assert.equal(groupedUsages.length >= 3, true)
  assert.equal(searchableUsages.length >= 3, true)
  assert.equal(searchPlaceholderUsages.length >= 3, true)
})

test('shared dropdown widgets support provider grouping and search filtering', () => {
  const headerDropdownPath = resolve(process.cwd(), 'src/components/ui/HeaderDropdown.vue')
  const multiSelectDropdownPath = resolve(process.cwd(), 'src/components/ui/MultiSelectDropdown.vue')
  const headerSource = readFileSync(headerDropdownPath, 'utf-8')
  const multiSource = readFileSync(multiSelectDropdownPath, 'utf-8')

  assert.equal(headerSource.includes('groupByProvider'), true)
  assert.equal(headerSource.includes('groupedFilteredOptions'), true)
  assert.equal(headerSource.includes('searchQuery'), true)
  assert.equal(headerSource.includes("default: 'Search models'"), true)
  assert.equal(headerSource.includes("default: 'No results found'"), true)
  assert.equal(headerSource.includes('formatProviderLabel'), true)
  assert.equal(headerSource.includes('sticky top-0 z-10'), true)

  assert.equal(multiSource.includes('groupByProvider'), true)
  assert.equal(multiSource.includes('groupedFilteredOptions'), true)
  assert.equal(multiSource.includes('searchQuery'), true)
  assert.equal(multiSource.includes("default: 'Search models'"), true)
  assert.equal(multiSource.includes("default: 'No results found'"), true)
  assert.equal(multiSource.includes('formatProviderLabel'), true)
  assert.equal(multiSource.includes('sticky top-0 z-10'), true)
})
