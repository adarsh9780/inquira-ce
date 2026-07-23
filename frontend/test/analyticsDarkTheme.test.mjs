import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

function themeToken(source, tokenName) {
  const midnightBlock = source.match(/:root\[data-theme="midnight"\],[\s\S]*?\{([\s\S]*?)\n\}/)?.[1] || ''
  return midnightBlock.match(new RegExp(`${tokenName}:\\s*(#[0-9A-Fa-f]{6})`))?.[1] || ''
}

function relativeLuminance(hex) {
  const channels = hex.slice(1).match(/.{2}/g).map((value) => Number.parseInt(value, 16) / 255)
  const linear = channels.map((value) => (
    value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  ))
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

function contrastRatio(first, second) {
  const lighter = Math.max(relativeLuminance(first), relativeLuminance(second))
  const darker = Math.min(relativeLuminance(first), relativeLuminance(second))
  return (lighter + 0.05) / (darker + 0.05)
}

test('analytics dark palette keeps primary and secondary text readable on working surfaces', () => {
  const source = read('src/style.css')
  const base = themeToken(source, '--color-base')
  const surface = themeToken(source, '--color-surface')
  const textMain = themeToken(source, '--color-text-main')
  const textMuted = themeToken(source, '--color-text-muted')

  assert.equal(Boolean(base && surface && textMain && textMuted), true)
  assert.ok(contrastRatio(textMain, base) >= 7)
  assert.ok(contrastRatio(textMain, surface) >= 7)
  assert.ok(contrastRatio(textMuted, base) >= 4.5)
  assert.ok(contrastRatio(textMuted, surface) >= 4.5)
})

test('analytics surfaces have dedicated table and chart colors instead of generic UI fills', () => {
  const styleSource = read('src/style.css')
  const tableSource = read('src/components/analysis/table/DataTable.vue')

  assert.equal(styleSource.includes('--color-chart-series-8: #6DC5D9;'), true)
  assert.equal(styleSource.includes('--color-chart-grid: #243341;'), true)
  assert.equal(styleSource.includes('--color-data-grid-header: #172430;'), true)
  assert.equal(styleSource.includes('--color-data-grid-row-alt: #121D27;'), true)
  assert.equal(styleSource.includes('--color-data-grid-row-hover: #1C2A38;'), true)
  assert.equal(tableSource.includes('background: var(--color-data-grid-header);'), true)
  assert.equal(tableSource.includes('background: var(--color-data-grid-row-alt);'), true)
  assert.equal(tableSource.includes('background: var(--color-data-grid-row-hover);'), true)
})

test('charts and terminal refresh their embedded themes when appearance changes', () => {
  const figureSource = read('src/components/analysis/FigureTab.vue')
  const terminalSource = read('src/components/analysis/NativeTerminalPane.vue')

  assert.equal(figureSource.includes('() => preferencesStore.uiTheme'), true)
  assert.equal(figureSource.includes('const themeMode = PLOTLY_THEME_MODE.SOFT'), true)
  assert.equal(figureSource.includes('await renderPlot()'), true)
  assert.equal(terminalSource.includes('function syncTerminalTheme()'), true)
  assert.equal(terminalSource.includes('terminal.options.theme = getTerminalVisualTheme()'), true)
  assert.equal(terminalSource.includes('() => [preferencesStore.uiTheme, preferencesStore.uiCodeFont]'), true)
})
