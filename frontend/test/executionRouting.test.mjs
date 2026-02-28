import test from 'node:test'
import assert from 'node:assert/strict'

import {
  decideExecutionTab,
  decideExecutionTabWithSelection,
  prioritizeByName,
  resolvePreferredArtifactNames,
} from '../src/utils/executionRouting.js'

test('decideExecutionTab routes dataframe, figure, error and no-result cases', () => {
  assert.equal(
    decideExecutionTab({ resultType: 'DataFrame', resultKind: 'dataframe', hasError: false, hasDataframes: true, hasFigures: false }),
    'table',
  )
  assert.equal(
    decideExecutionTab({ resultType: 'Figure', resultKind: 'figure', hasError: false, hasDataframes: false, hasFigures: true }),
    'figure',
  )
  assert.equal(
    decideExecutionTab({ resultType: 'scalar', hasError: false, hasDataframes: false, hasFigures: false }),
    null,
  )
  assert.equal(
    decideExecutionTab({ resultType: null, hasError: false, hasDataframes: false, hasFigures: false }),
    null,
  )
  assert.equal(
    decideExecutionTab({ resultType: 'DataFrame', hasError: true, hasDataframes: true, hasFigures: false }),
    'terminal',
  )
})

test('resolvePreferredArtifactNames matches dataframe result to the same dataframe variable', () => {
  const viewModel = {
    dataframes: [
      { name: 'old_df', data: { columns: ['a'], data: [{ a: 99 }] } },
      { name: 'selected_df', data: { artifact_id: 'x', row_count: 2, columns: ['a'], data: [{ a: 1 }, { a: 2 }] } },
    ],
    figures: [],
  }
  const normalized = {
    result_type: 'DataFrame',
    result: { columns: ['a'], data: [{ a: 1 }, { a: 2 }] },
  }

  const preferred = resolvePreferredArtifactNames(viewModel, normalized)
  assert.equal(preferred.dataframeName, 'selected_df')
  assert.equal(preferred.figureName, null)
})

test('resolvePreferredArtifactNames prefers backend-provided result_name when available', () => {
  const viewModel = {
    dataframes: [
      { name: 'old_df', data: { columns: ['a'], data: [{ a: 99 }] } },
      { name: 'top_batsmen', data: { artifact_id: 'x', row_count: 2, columns: ['a'], data: [{ a: 1 }, { a: 2 }] } },
    ],
    figures: [],
  }
  const normalized = {
    result_kind: 'dataframe',
    result_name: 'top_batsmen',
    result_type: 'scalar',
    result: 'text repr',
  }

  const preferred = resolvePreferredArtifactNames(viewModel, normalized)
  assert.equal(preferred.dataframeName, 'top_batsmen')
})

test('resolvePreferredArtifactNames matches figure result to the same figure variable', () => {
  const sharedFigure = {
    data: [{ type: 'bar', x: ['a'], y: [1] }],
    layout: { title: { text: 'Sales' } },
  }
  const viewModel = {
    dataframes: [],
    figures: [
      { name: 'other_fig', data: { data: [{ type: 'scatter', x: [1], y: [1] }], layout: {} } },
      { name: 'selected_fig', data: sharedFigure },
    ],
  }
  const normalized = {
    result_type: 'Figure',
    result: sharedFigure,
  }

  const preferred = resolvePreferredArtifactNames(viewModel, normalized)
  assert.equal(preferred.figureName, 'selected_fig')
  assert.equal(preferred.dataframeName, null)
})

test('prioritizeByName moves preferred artifact to front', () => {
  const items = [{ name: 'a' }, { name: 'b' }, { name: 'c' }]
  const ordered = prioritizeByName(items, 'c')
  assert.deepEqual(ordered.map((x) => x.name), ['c', 'a', 'b'])
})

test('decideExecutionTabWithSelection routes identifier selections to table/figure', () => {
  assert.equal(
    decideExecutionTabWithSelection({
      resultType: 'scalar',
      resultKind: 'dataframe',
      resultName: 'top_batsmen',
      hasError: false,
      hasDataframes: true,
      hasFigures: false,
      selectedCode: 'top_batsmen',
      dataframeNames: ['top_batsmen'],
      figureNames: [],
    }),
    'table',
  )

  assert.equal(
    decideExecutionTabWithSelection({
      resultType: null,
      resultKind: 'figure',
      resultName: 'fig',
      hasError: false,
      hasDataframes: false,
      hasFigures: true,
      selectedCode: 'fig',
      dataframeNames: [],
      figureNames: ['fig'],
    }),
    'figure',
  )
})

test('decideExecutionTabWithSelection keeps tab for non-identifier selections', () => {
  assert.equal(
    decideExecutionTabWithSelection({
      resultType: 'scalar',
      hasError: false,
      hasDataframes: true,
      hasFigures: false,
      selectedCode: 'top_batsmen.head()',
      dataframeNames: ['top_batsmen'],
      figureNames: [],
    }),
    null,
  )
})
