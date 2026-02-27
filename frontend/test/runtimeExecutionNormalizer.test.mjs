import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizeExecutionResponse } from '../src/utils/runtimeExecution.js'

test('normalizes stdout/stderr into legacy output field', () => {
  const normalized = normalizeExecutionResponse({
    success: true,
    stdout: 'hello',
    stderr: 'warn',
    error: null,
    result: null,
    result_type: null,
  })

  assert.equal(normalized.output, 'hello\nwarn')
})

test('maps DataFrame result to variables.dataframes', () => {
  const df = { columns: ['a'], index: [0], data: [[1]] }
  const normalized = normalizeExecutionResponse({
    success: true,
    stdout: '',
    stderr: '',
    error: null,
    result: df,
    result_type: 'DataFrame',
  })

  assert.deepEqual(normalized.variables.dataframes.result, [{ a: 1 }])
  assert.equal(Object.keys(normalized.variables.figures).length, 0)
  assert.equal(Object.keys(normalized.variables.scalars).length, 0)
})

test('maps scalar results to variables.scalars when type is missing', () => {
  const normalized = normalizeExecutionResponse({
    success: true,
    stdout: '',
    stderr: '',
    error: null,
    result: 42,
  })

  assert.equal(normalized.variables.scalars.result, 42)
})

test('preserves explicit variable buckets from payload', () => {
  const fig = { data: [{ x: [1], y: [2] }], layout: { title: 't' } }
  const normalized = normalizeExecutionResponse({
    success: true,
    stdout: '',
    stderr: '',
    variables: {
      dataframes: { summary: { columns: ['a'], data: [[1]] } },
      figures: { chart: fig },
      scalars: { answer: 42 },
    },
  })

  assert.deepEqual(normalized.variables.dataframes.summary, [{ a: 1 }])
  assert.deepEqual(normalized.variables.figures.chart, fig)
  assert.equal(normalized.variables.scalars.answer, 42)
})

test('unpacks variable bundle when returned inside result', () => {
  const normalized = normalizeExecutionResponse({
    success: true,
    stdout: '',
    stderr: '',
    result_type: 'scalar',
    result: {
      dataframes: { summary: { columns: ['a'], data: [[1]] } },
      figures: { chart: { data: [{ x: [1], y: [2] }], layout: {} } },
      scalars: { rows: 1 },
    },
  })

  assert.equal(Object.keys(normalized.variables.scalars).includes('result'), false)
  assert.equal(normalized.variables.scalars.rows, 1)
  assert.equal(Object.keys(normalized.variables.dataframes).length, 1)
  assert.equal(Object.keys(normalized.variables.figures).length, 1)
})
