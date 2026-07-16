import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizePlotlyFigure } from '../src/utils/figurePayload.js'

test('normalizePlotlyFigure accepts native plotly figure objects', () => {
  const input = { data: [{ x: [1], y: [2], type: 'bar' }], layout: { title: 'Sales' } }
  const normalized = normalizePlotlyFigure(input)

  assert.deepEqual(normalized?.data, input.data)
  assert.deepEqual(normalized?.layout, input.layout)
})

test('normalizePlotlyFigure parses stringified figure payload', () => {
  const input = JSON.stringify({
    data: [{ x: [1, 2], y: [3, 4], type: 'scatter' }],
    layout: { title: 'Trend' },
  })
  const normalized = normalizePlotlyFigure(input)

  assert.equal(Array.isArray(normalized?.data), true)
  assert.equal(normalized?.layout?.title, 'Trend')
})

test('normalizePlotlyFigure unwraps nested artifact payload wrappers', () => {
  const input = {
    payload: {
      figure: JSON.stringify({
        data: [{ values: [60, 40], labels: ['A', 'B'], type: 'pie' }],
        layout: {},
      }),
    },
  }
  const normalized = normalizePlotlyFigure(input)

  assert.equal(Array.isArray(normalized?.data), true)
  assert.equal(normalized?.data?.[0]?.type, 'pie')
})

test('normalizePlotlyFigure returns null for non-plotly payloads', () => {
  assert.equal(normalizePlotlyFigure({ hello: 'world' }), null)
  assert.equal(normalizePlotlyFigure('not-json'), null)
})
