import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildBrowserDataPath,
  hasUsableIngestedColumns,
  inferTableNameFromDataPath
} from '../src/utils/chatBootstrap.js'

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

test('inferTableNameFromDataPath resolves browser:// table paths', () => {
  assert.equal(inferTableNameFromDataPath('browser://ball_by_ball_ipl'), 'ball_by_ball_ipl')
})

test('inferTableNameFromDataPath resolves legacy /browser:/ table paths', () => {
  assert.equal(inferTableNameFromDataPath('/browser:/ball_by_ball_ipl'), 'ball_by_ball_ipl')
})

test('inferTableNameFromDataPath falls back to filename without extension', () => {
  assert.equal(inferTableNameFromDataPath('/tmp/My Dataset.csv'), 'My Dataset')
})
