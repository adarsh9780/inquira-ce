import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists table viewport and per-artifact page offsets', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(appStorePath, 'utf-8')

  assert.equal(source.includes('const tablePageOffsets = ref({})'), true)
  assert.equal(source.includes('table_page_offsets: tablePageOffsets.value || {}'), true)
  assert.equal(source.includes('function setTablePageOffset(workspaceId, artifactId, page) {'), true)
  assert.equal(source.includes('function getTablePageOffset(workspaceId, artifactId) {'), true)
  assert.equal(source.includes('function setTableViewport(start, end, total) {'), true)
  assert.equal(source.includes('function clearTableViewport() {'), true)
})
