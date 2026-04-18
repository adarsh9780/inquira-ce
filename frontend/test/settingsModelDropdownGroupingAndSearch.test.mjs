import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings model selectors use shared ModelSelector for main model and searchable HeaderDropdown for lite model', () => {
  const apiTabPath = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(apiTabPath, 'utf-8')

  const groupedUsages = source.match(/:group-by-provider="true"/g) ?? []
  const searchableUsages = source.match(/:searchable="true"/g) ?? []

  assert.equal(source.includes('<ModelSelector'), true)
  assert.equal(source.includes(':search-loading="appStore.providerModelSearchLoading"'), true)
  assert.equal(groupedUsages.length >= 1, true)
  assert.equal(searchableUsages.length >= 1, true)
  assert.equal(source.includes('search-placeholder="Search models"'), true)
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
  assert.equal(headerSource.includes('sharedProviderLabel'), true)
  assert.equal(headerSource.includes('sticky top-0 z-10'), true)

  assert.equal(multiSource.includes('groupByProvider'), true)
  assert.equal(multiSource.includes('groupedFilteredOptions'), true)
  assert.equal(multiSource.includes('searchQuery'), true)
  assert.equal(multiSource.includes("default: 'Search models'"), true)
  assert.equal(multiSource.includes("default: 'No results found'"), true)
  assert.equal(multiSource.includes('formatProviderLabel'), true)
  assert.equal(multiSource.includes('sticky top-0 z-10'), true)
})
