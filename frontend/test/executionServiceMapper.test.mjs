import test from 'node:test'
import assert from 'node:assert/strict'

import { mapExecutionServiceResponse } from '../src/utils/executionServiceMapper.js'

test('mapExecutionServiceResponse preserves variables bundle from api response', () => {
  const mapped = mapExecutionServiceResponse({
    success: true,
    stdout: '',
    stderr: '',
    error: null,
    result: null,
    result_type: null,
    variables: {
      dataframes: { top_batsmen_df: { artifact_id: 'a1', row_count: 10, data: [{ Batter: 'A' }] } },
      figures: { chart: { data: [], layout: {} } },
      scalars: { rows: 10 },
    },
  })

  assert.equal(Boolean(mapped.variables?.dataframes?.top_batsmen_df), true)
  assert.equal(mapped.variables.dataframes.top_batsmen_df.artifact_id, 'a1')
  assert.equal(mapped.variables.scalars.rows, 10)
})
