import test from 'node:test'
import assert from 'node:assert/strict'

import { compileChartSpec, parseChartSpec } from '../src/utils/chartSpec.ts'

const baseSpec = {
  schema: 'inquira.chart/v1',
  data: { logical_name: 'sales_summary' },
  mark: 'bar',
  encoding: {
    x: { field: 'region', type: 'nominal' },
    y: { field: 'revenue', type: 'quantitative', sort: 'descending' },
  },
  title: 'Revenue by region',
  options: { orientation: 'vertical', stacking: 'grouped', show_markers: true },
}

test('chart spec compiler creates deterministic Plotly JSON from constrained fields', () => {
  const figure = compileChartSpec(baseSpec, [
    { region: 'West', revenue: 20 },
    { region: 'East', revenue: 40 },
  ])

  assert.deepEqual(figure.data, [{ type: 'bar', x: ['East', 'West'], y: [40, 20] }])
  assert.equal(figure.layout.title.text, 'Revenue by region')
  assert.equal(figure.layout.barmode, 'group')
  assert.equal(figure.config.displaylogo, false)
})

test('chart spec parser rejects raw Plotly styling and unsupported fields', () => {
  assert.throws(
    () => parseChartSpec({ ...baseSpec, layout: { paper_bgcolor: 'red' } }),
    /unsupported field\(s\): layout/,
  )
})

test('chart spec compiler reports missing source fields before rendering', () => {
  assert.throws(
    () => compileChartSpec(baseSpec, [{ region: 'West', profit: 20 }]),
    /does not contain chart field\(s\): revenue/,
  )
})

test('heatmap specs require one source row for each visual cell', () => {
  const heatmap = {
    ...baseSpec,
    mark: 'heatmap',
    encoding: {
      x: { field: 'month', type: 'ordinal' },
      y: { field: 'region', type: 'nominal' },
      color: { field: 'revenue', type: 'quantitative' },
    },
    title: 'Revenue heatmap',
  }
  assert.throws(
    () => compileChartSpec(heatmap, [
      { month: 'Jan', region: 'West', revenue: 10 },
      { month: 'Jan', region: 'West', revenue: 20 },
    ]),
    /one row for each x\/y combination/,
  )
})
