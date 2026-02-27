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

  assert.deepEqual(normalized.variables.dataframes.result, df)
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

