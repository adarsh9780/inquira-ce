import test from 'node:test'
import assert from 'node:assert/strict'

import { buildExecutionViewModel } from '../src/utils/executionViewModel.js'

test('buildExecutionViewModel parses variable buckets and renders output text', () => {
  const view = buildExecutionViewModel(
    {
      execution_time: 0.25,
      output: 'hello',
      error: null,
      variables: {
        dataframes: {
          result: JSON.stringify({ columns: ['a'], index: [0], data: [[1]] }),
        },
        figures: {},
        scalars: { answer: 42 },
      },
    },
    {
      includeVariableSummary: true,
    },
  )

  assert.equal(view.dataframes.length, 1)
  assert.equal(view.scalars.length, 1)
  assert.equal(view.figures.length, 0)
  assert.equal(view.counts.dataframes, 1)
  assert.equal(view.counts.scalars, 1)
  assert.equal(view.output.includes('Execution time: 0.250s'), true)
  assert.equal(view.output.includes('Variables created: 1 dataframe(s), 0 figure(s), 1 scalar(s)'), true)
})

test('buildExecutionViewModel reports parse errors for invalid json bucket items', () => {
  const view = buildExecutionViewModel({
    output: '',
    error: null,
    variables: {
      dataframes: {
        bad: '{not json',
      },
      figures: {},
      scalars: {},
    },
  })

  assert.equal(view.dataframes.length, 0)
  assert.equal(view.output.includes('⚠️ Failed to parse dataframe data.'), true)
})

