import test from 'node:test'
import assert from 'node:assert/strict'

import {
  applyPlotlyTheme,
  applyPlotlyConfigTheme,
  PLOTLY_THEME_MODE,
} from '../src/utils/plotlyTheme.js'

test('soft plotly theme updates colors without forcing typography sizes', () => {
  const input = {
    data: [{ type: 'scatter', x: [1, 2], y: [3, 4], mode: 'lines+markers' }],
    layout: {
      font: { size: 18, color: '#101010' },
      title: { text: 'Revenue', font: { size: 20, color: '#101010' } },
      xaxis: { tickfont: { size: 15, color: '#111111' } },
    },
  }
  const original = JSON.parse(JSON.stringify(input))

  const themed = applyPlotlyTheme(input, { mode: PLOTLY_THEME_MODE.SOFT })

  assert.equal(themed.layout.paper_bgcolor, '#FFFFFF')
  assert.equal(themed.layout.plot_bgcolor, '#FFFFFF')
  assert.deepEqual(
    themed.layout.colorway,
    ['#D47948', '#3B82F6', '#0EA5E9', '#22C55E', '#F59E0B', '#EF4444', '#14B8A6', '#6366F1'],
  )
  assert.equal(themed.layout.font.size, 18)
  assert.equal(themed.layout.font.color, '#18181B')
  assert.equal(themed.layout.title.font.size, 20)
  assert.equal(themed.layout.title.font.color, '#18181B')
  assert.equal(themed.layout.xaxis.tickfont.size, 15)
  assert.equal(themed.layout.xaxis.tickfont.color, '#52525B')
  assert.equal(themed.layout.xaxis.title.font.color, '#18181B')
  assert.deepEqual(
    themed.layout.colorscale.sequential,
    [
      [0, '#FFF7ED'],
      [0.35, '#FED7AA'],
      [0.68, '#E7A06A'],
      [1, '#D47948'],
    ],
  )
  assert.deepEqual(input, original)
})

test('hard plotly theme adds sensible layout defaults for chart readability', () => {
  const input = {
    data: [{ type: 'scatter', x: [1, 2], y: [10, 20], mode: 'lines+markers' }],
    layout: {
      margin: { l: 92 },
      title: { text: 'Trend' },
    },
  }

  const themed = applyPlotlyTheme(input, { mode: PLOTLY_THEME_MODE.HARD, context: 'panel' })

  assert.equal(typeof themed.layout.font.family, 'string')
  assert.equal(themed.layout.font.family.length > 0, true)
  assert.equal(themed.layout.font.size, 12)
  assert.equal(themed.layout.title.font.size, 14)
  assert.equal(themed.layout.title.x, 0.02)
  assert.equal(themed.layout.legend.orientation, 'h')
  assert.equal(themed.layout.margin.l, 92)
  assert.equal(themed.layout.margin.r, 28)
  assert.equal(themed.layout.margin.t, 44)
  assert.equal(themed.layout.xaxis.tickfont.size, 11)
  assert.equal(themed.layout.yaxis.title.standoff, 10)
  assert.equal(themed.data[0].line.width, 2)
  assert.equal(themed.data[0].marker.size, 7)
})

test('plotly config theme merges modebar removals and image defaults', () => {
  const config = applyPlotlyConfigTheme(
    {
      modeBarButtonsToRemove: ['zoomIn2d', 'select2d'],
      toImageButtonOptions: { width: 2000 },
    },
    { mode: PLOTLY_THEME_MODE.HARD },
  )

  assert.deepEqual(config.modeBarButtonsToRemove, ['pan2d', 'lasso2d', 'select2d', 'zoomIn2d'])
  assert.equal(config.displayModeBar, true)
  assert.equal(config.displaylogo, false)
  assert.equal(config.responsive, true)
  assert.equal(config.toImageButtonOptions.format, 'png')
  assert.equal(config.toImageButtonOptions.width, 2000)
  assert.equal(config.toImageButtonOptions.height, 900)
  assert.equal(config.toImageButtonOptions.scale, 2)
})

test('invalid mode falls back to soft theming', () => {
  const themed = applyPlotlyTheme(
    { data: [{ x: [1], y: [2] }], layout: {} },
    { mode: 'unsupported-mode' },
  )

  assert.equal(themed.layout.paper_bgcolor, '#FFFFFF')
  assert.equal(themed.layout.font.size, undefined)
})

test('single bar trace collapses continuous bar coloring into one UI accent color', () => {
  const input = {
    data: [
      {
        type: 'bar',
        x: ['Sandeep Sharma', 'A Nehra', 'Mohammed Shami'],
        y: [7, 6, 5],
        marker: {
          color: [129.85, 104.2, 131.1],
          colorscale: 'Plasma',
          colorbar: { title: { text: "Kohli's Strike Rate" } },
          cmin: 90,
          cmax: 190,
        },
      },
    ],
    layout: {
      coloraxis: {
        colorscale: 'Plasma',
      },
    },
  }

  const themed = applyPlotlyTheme(input, { mode: PLOTLY_THEME_MODE.SOFT })

  assert.equal(themed.data[0].marker.color, '#D47948')
  assert.equal(themed.data[0].marker.colorscale, undefined)
  assert.equal(themed.data[0].marker.colorbar, undefined)
  assert.equal(themed.data[0].marker.cmin, undefined)
  assert.equal(themed.data[0].marker.cmax, undefined)
  assert.equal(themed.layout.coloraxis, undefined)
})

test('plotly theme reads analytics colors and elevated legend surface from the active UI theme', () => {
  const darkTokens = {
    '--color-base': '#101923',
    '--color-surface': '#16212C',
    '--color-panel-elevated': '#1B2835',
    '--color-border': '#273543',
    '--color-border-hover': '#3B4D60',
    '--color-text-main': '#E7EDF5',
    '--color-text-muted': '#97A6B8',
    '--color-accent': '#D98958',
    '--color-chart-grid': '#243341',
    '--color-chart-zero': '#3B4F62',
    '--color-chart-paper': '#121C27',
    '--color-chart-plot': '#0F1822',
    '--color-chart-tooltip-bg': '#233342',
    '--color-chart-tooltip-border': '#476078',
    '--font-ui': '"Premium Sans", sans-serif',
    '--color-chart-series-1': '#78A9E6',
    '--color-chart-series-2': '#E09963',
    '--color-chart-sequential-1': '#13243A',
    '--color-chart-sequential-2': '#275F93',
    '--color-chart-sequential-3': '#4F91CB',
    '--color-chart-sequential-4': '#9CCAF2',
    '--color-chart-diverging-low': '#78A9E6',
    '--color-chart-diverging-mid': '#1B2835',
    '--color-chart-diverging-high': '#E09963',
  }
  const previousWindow = globalThis.window
  const previousDocument = globalThis.document
  const previousGetComputedStyle = globalThis.getComputedStyle
  globalThis.window = {}
  globalThis.document = { documentElement: {} }
  globalThis.getComputedStyle = () => ({
    getPropertyValue: (tokenName) => darkTokens[tokenName] || '',
  })

  try {
    const themed = applyPlotlyTheme(
      { data: [{ type: 'scatter', x: [1, 2], y: [2, 4] }], layout: {} },
      { mode: PLOTLY_THEME_MODE.SOFT },
    )

    assert.equal(themed.layout.paper_bgcolor, '#121C27')
    assert.equal(themed.layout.plot_bgcolor, '#0F1822')
    assert.equal(themed.layout.legend.bgcolor, '#1B2835')
    assert.equal(themed.layout.hoverlabel.bgcolor, '#233342')
    assert.equal(themed.layout.hoverlabel.bordercolor, '#476078')
    assert.equal(themed.layout.font.family, '"Premium Sans", sans-serif')
    assert.equal(themed.layout.xaxis.gridcolor, '#243341')
    assert.equal(themed.layout.xaxis.zerolinecolor, '#3B4F62')
    assert.equal(themed.layout.colorway[0], '#78A9E6')
    assert.equal(themed.layout.colorway[1], '#E09963')
    assert.equal(themed.layout.colorscale.diverging[1][1], '#1B2835')
  } finally {
    globalThis.window = previousWindow
    globalThis.document = previousDocument
    globalThis.getComputedStyle = previousGetComputedStyle
  }
})

test('plotly typography follows live font token changes without a page reload', () => {
  let selectedFont = '"Manrope", sans-serif'
  const previousWindow = globalThis.window
  const previousDocument = globalThis.document
  const previousGetComputedStyle = globalThis.getComputedStyle
  globalThis.window = {}
  globalThis.document = { documentElement: {} }
  globalThis.getComputedStyle = () => ({
    getPropertyValue: (tokenName) => tokenName === '--font-ui' ? selectedFont : '',
  })

  try {
    const first = applyPlotlyTheme({ data: [], layout: {} }, { mode: PLOTLY_THEME_MODE.HARD })
    selectedFont = '"IBM Plex Sans", sans-serif'
    const second = applyPlotlyTheme({ data: [], layout: {} }, { mode: PLOTLY_THEME_MODE.HARD })

    assert.equal(first.layout.font.family, '"Manrope", sans-serif')
    assert.equal(second.layout.font.family, '"IBM Plex Sans", sans-serif')
  } finally {
    globalThis.window = previousWindow
    globalThis.document = previousDocument
    globalThis.getComputedStyle = previousGetComputedStyle
  }
})
