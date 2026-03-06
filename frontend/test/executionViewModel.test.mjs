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

test('buildExecutionViewModel prefers artifact-backed dataframe and figure entries', () => {
  const view = buildExecutionViewModel({
    output: '',
    error: null,
    variables: {
      dataframes: {},
      figures: {},
      scalars: {},
    },
    artifacts: [
      {
        artifact_id: 'df-1',
        kind: 'dataframe',
        logical_name: 'summary_df',
        row_count: 120,
        schema: [{ name: 'a', dtype: 'INTEGER' }],
        preview_rows: [[1], [2]],
      },
      {
        artifact_id: 'fig-1',
        kind: 'figure',
        logical_name: 'trend_fig',
        payload: { figure: { data: [{ x: [1], y: [2] }], layout: { title: { text: 'Trend' } } } },
      },
    ],
  })

  assert.equal(view.dataframes.length, 1)
  assert.equal(view.dataframes[0].name, 'summary_df')
  assert.equal(view.dataframes[0].data.artifact_id, 'df-1')
  assert.deepEqual(view.dataframes[0].data.data, [{ a: 1 }, { a: 2 }])
  assert.equal(view.figures.length, 1)
  assert.equal(view.figures[0].artifact_id, 'fig-1')
  assert.equal(view.counts.dataframes, 1)
  assert.equal(view.counts.figures, 1)
})
