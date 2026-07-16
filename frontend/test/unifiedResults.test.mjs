import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildOtherExecutionItems,
  buildUnifiedResultItems,
  executionLogResultId,
  preferredExecutionResultId,
  resultPaneForKind,
} from '../src/utils/unifiedResults.js'

test('buildOtherExecutionItems keeps code with non-visual output and excludes visual-only runs', () => {
  const items = buildOtherExecutionItems({
    terminalEntries: [
      {
        id: 'table-only',
        kind: 'output',
        source: 'analysis',
        label: 'Code run',
        command: 'result = query.df()\nresult',
        runId: 'run-table',
        status: 'success',
        hasTableOutput: true,
      },
      {
        id: 'mixed-run',
        kind: 'output',
        source: 'analysis',
        label: 'Code run',
        command: 'result = query.df()\nprint("rows=2")\nresult',
        runId: 'run-mixed',
        status: 'success',
        stdout: 'rows=2',
        hasTableOutput: true,
      },
    ],
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].id, 'execution:mixed-run')
  assert.equal(items[0].code.includes('print("rows=2")'), true)
  assert.equal(items[0].stdout, 'rows=2')
})

test('buildOtherExecutionItems retains scalar output on its originating execution', () => {
  const items = buildOtherExecutionItems({
    terminalEntries: [{
      id: 'scalar-run',
      kind: 'output',
      source: 'analysis',
      label: 'Selection run',
      command: 'total = 42\ntotal',
      runId: 'run-scalar',
      status: 'success',
      scalarOutputs: [{ name: 'total', value: 42, runId: 'run-scalar', result_type: 'int' }],
    }],
    scalars: [{ name: 'total', value: 42, runId: 'run-scalar', result_type: 'int' }],
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].code, 'total = 42\ntotal')
  assert.equal(items[0].scalarOutputs.length, 1)
  assert.equal(items[0].scalarOutputs[0].value, 42)
  assert.equal(items[0].scalarOutputs[0].type, 'int')
})

test('buildOtherExecutionItems restores persisted scalar artifacts with turn code', () => {
  const items = buildOtherExecutionItems({
    activeTurnArtifacts: [{
      artifact_id: 'scalar-artifact',
      kind: 'scalar',
      display_name: 'conversion_rate',
      payload: { value: 0.42, type: 'float' },
      created_at: '2026-07-16T08:00:00Z',
    }],
    fallbackCode: 'conversion_rate = converted / total\nconversion_rate',
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].code.includes('conversion_rate ='), true)
  assert.equal(items[0].scalarOutputs[0].name, 'conversion_rate')
  assert.equal(items[0].scalarOutputs[0].value, 0.42)
})

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
