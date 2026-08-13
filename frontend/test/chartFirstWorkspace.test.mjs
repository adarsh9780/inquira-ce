import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const rightPane = readFileSync(new URL('../src/components/layout/WorkspaceRightPane.vue', import.meta.url), 'utf8')
const figureTab = readFileSync(new URL('../src/components/analysis/FigureTab.vue', import.meta.url), 'utf8')

test('results navigation presents charts before supporting tables and runs', () => {
  const chartIndex = rightPane.indexOf("value: 'chart', label: 'Charts'")
  const tableIndex = rightPane.indexOf("value: 'table', label: 'Tables'")
  const runsIndex = rightPane.indexOf("value: 'runs', label: 'Runs'")

  assert.ok(chartIndex > 0)
  assert.ok(chartIndex < tableIndex)
  assert.ok(tableIndex < runsIndex)
  assert.match(rightPane, /watch\(chartResultCount[\s\S]*uiStore\.setDataPane\('figure'\)/)
})

test('chart editor exposes source data and validated spec without displacing preview', () => {
  assert.match(figureTab, /aria-label="Chart preview"/)
  assert.match(figureTab, /aria-label="Chart editor"/)
  assert.match(figureTab, /> Data\s*<\/button>/)
  assert.match(figureTab, /> Spec\s*<\/button>/)
  assert.match(figureTab, /compileChartSpec\(parsed, sourceRows\.value\)/)
  assert.match(figureTab, /Apply revision/)
  assert.match(figureTab, /data-toolbar-mode='minimal'/)
})

test('chart canvas uses the enforced Inquira Plotly theme', () => {
  assert.match(figureTab, /const themeMode = PLOTLY_THEME_MODE\.HARD/)
  assert.doesNotMatch(figureTab, /const themeMode = PLOTLY_THEME_MODE\.SOFT/)
})
