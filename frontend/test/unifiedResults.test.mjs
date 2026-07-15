import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildUnifiedResultItems,
  executionLogResultId,
  preferredExecutionResultId,
  resultPaneForKind,
} from '../src/utils/unifiedResults.js'

test('buildUnifiedResultItems normalizes one manual run without duplicating artifacts', () => {
  const items = buildUnifiedResultItems({
    dataframes: [{ name: 'customers', runId: 'run-1', data: { artifact_id: 'df-1', data: [{ id: 1 }] } }],
    figures: [{ name: 'revenue', runId: 'run-1', artifact_id: 'fig-1', data: { data: [] } }],
    scalars: [{ name: 'total', runId: 'run-1', value: 42 }],
    activeTurnArtifacts: [
      { artifact_id: 'df-1', kind: 'dataframe', logical_name: 'customers' },
      { artifact_id: 'fig-1', kind: 'figure', logical_name: 'revenue' },
    ],
    terminalEntries: [{
      id: 'entry-1',
      kind: 'output',
      source: 'analysis',
      label: 'Code run',
      runId: 'run-1',
      status: 'success',
      stdout: 'done',
    }],
  })

  assert.deepEqual(items.map((item) => item.kind).sort(), ['chart', 'log', 'scalar', 'table'])
  assert.equal(items.filter((item) => item.id === 'table:df-1').length, 1)
  assert.equal(items.filter((item) => item.id === 'chart:fig-1').length, 1)
  assert.equal(items.find((item) => item.id === 'log:entry-1')?.runId, 'run-1')
})

test('preferredExecutionResultId honors errors, explicit results, and artifact fallback order', () => {
  const items = buildUnifiedResultItems({
    dataframes: [{ name: 'customers', runId: 'run-2', data: { artifact_id: 'df-2' } }],
    figures: [{ name: 'revenue', runId: 'run-2', artifact_id: 'fig-2', data: { data: [] } }],
    terminalEntries: [{
      id: 'entry-2',
      kind: 'output',
      source: 'analysis',
      runId: 'run-2',
      status: 'error',
      stderr: 'boom',
    }],
  })

  assert.equal(preferredExecutionResultId({
    items,
    runId: 'run-2',
    hasError: true,
    logEntryId: 'entry-2',
  }), 'log:entry-2')

  assert.equal(preferredExecutionResultId({
    items,
    runId: 'run-2',
    resultKind: 'dataframe',
    resultName: 'customers',
    logEntryId: 'entry-2',
  }), 'table:df-2')

  assert.equal(preferredExecutionResultId({
    items,
    runId: 'run-2',
    logEntryId: 'entry-2',
  }), 'chart:fig-2')
})

test('result helpers preserve output routing compatibility', () => {
  assert.equal(executionLogResultId('entry-3'), 'log:entry-3')
  assert.equal(resultPaneForKind('table'), 'table')
  assert.equal(resultPaneForKind('chart'), 'figure')
  assert.equal(resultPaneForKind('scalar'), 'output')
})
