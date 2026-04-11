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

  assert.equal(themed.layout.paper_bgcolor, '#FFFEFC')
  assert.equal(themed.layout.plot_bgcolor, '#FFFFFF')
  assert.deepEqual(
    themed.layout.colorway,
    ['#D47948', '#3B82F6', '#0EA5E9', '#22C55E', '#F59E0B', '#EF4444', '#14B8A6', '#6366F1'],
  )
  assert.equal(themed.layout.font.size, 18)
  assert.equal(themed.layout.font.color, '#27272A')
  assert.equal(themed.layout.title.font.size, 20)
  assert.equal(themed.layout.title.font.color, '#27272A')
  assert.equal(themed.layout.xaxis.tickfont.size, 15)
  assert.equal(themed.layout.xaxis.tickfont.color, '#71717A')
  assert.equal(themed.layout.xaxis.title.font.color, '#27272A')
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

  assert.equal(themed.layout.font.family.includes('Ubuntu'), true)
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

  assert.equal(themed.layout.paper_bgcolor, '#FFFEFC')
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
