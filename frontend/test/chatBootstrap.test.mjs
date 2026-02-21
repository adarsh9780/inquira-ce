import test from 'node:test'
import assert from 'node:assert/strict'

import { buildBrowserDataPath, hasUsableIngestedColumns } from '../src/utils/chatBootstrap.js'

test('buildBrowserDataPath builds virtual browser path from table name', () => {
  assert.equal(buildBrowserDataPath('sales_2025'), 'browser://sales_2025')
})

test('buildBrowserDataPath returns empty for blank input', () => {
  assert.equal(buildBrowserDataPath('   '), '')
})

test('hasUsableIngestedColumns validates ingested column metadata', () => {
  assert.equal(hasUsableIngestedColumns([{ name: 'country', type: 'VARCHAR' }]), true)
  assert.equal(hasUsableIngestedColumns([]), false)
  assert.equal(hasUsableIngestedColumns([{ type: 'VARCHAR' }]), false)
})
