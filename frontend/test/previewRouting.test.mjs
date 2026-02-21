import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPreviewSql, isBrowserDataPath } from '../src/utils/previewRouting.js'

test('isBrowserDataPath detects browser virtual paths', () => {
  assert.equal(isBrowserDataPath('browser://sales_data'), true)
  assert.equal(isBrowserDataPath('browser:/sales_data'), true)
  assert.equal(isBrowserDataPath('/browser:/sales_data'), true)
  assert.equal(isBrowserDataPath('/tmp/sales.csv'), false)
})

test('buildPreviewSql builds random sampling query', () => {
  const sql = buildPreviewSql('sales_data', 'random', 25)
  assert.match(sql, /ORDER BY RANDOM\(\)/)
  assert.match(sql, /LIMIT 25/)
})

test('buildPreviewSql builds first sample query', () => {
  const sql = buildPreviewSql('sales_data', 'first', 10)
  assert.equal(sql, 'SELECT * FROM sales_data LIMIT 10')
})
