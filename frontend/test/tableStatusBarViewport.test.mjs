import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar renders table row count and viewport window when table pane is active', () => {
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')

  const statusBar = readFileSync(statusBarPath, 'utf-8')
  const tableTab = readFileSync(tableTabPath, 'utf-8')

  assert.equal(statusBar.includes('const tableViewportLabel = computed(() => {'), true)
  assert.equal(statusBar.includes("if (appStore.dataPane !== 'table') return null"), true)
  assert.equal(statusBar.includes('appStore.tableRowCount'), true)
  assert.equal(statusBar.includes('Showing ${start.toLocaleString()}-${end.toLocaleString()} of ${total.toLocaleString()}'), true)

  assert.equal(tableTab.includes('Showing {{ windowStart.toLocaleString() }}-{{ windowEnd.toLocaleString() }}'), false)
  assert.equal(tableTab.includes('{{ rowCount.toLocaleString() }} rows'), false)
})
