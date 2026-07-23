import test from 'node:test'
import assert from 'node:assert/strict'

import { buildUserRunItems } from '../src/utils/unifiedResults.js'

test('buildUserRunItems keeps one manual run with text, table, and chart outputs', () => {
  const items = buildUserRunItems({
    terminalEntries: [
      {
        id: 'mixed-run',
        kind: 'output',
        source: 'analysis',
        origin: 'user',
        label: 'Code run',
        command: 'result = query.df()\nfig = chart(result)\nprint("rows=2")',
        runId: 'run-mixed',
        status: 'success',
        stdout: 'rows=2',
        tableOutputs: [{ name: 'result', data: [{ id: 1 }, { id: 2 }] }],
        chartOutputs: [{ name: 'figure', data: { data: [{ type: 'bar', y: [1, 2] }], layout: {} } }],
      },
    ],
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].id, 'execution:mixed-run')
  assert.equal(items[0].entryId, 'mixed-run')
  assert.equal(items[0].code.includes('print("rows=2")'), true)
  assert.equal(items[0].stdout, 'rows=2')
  assert.equal(items[0].tableOutputs[0].name, 'result')
  assert.equal(items[0].chartOutputs[0].name, 'figure')
})

test('buildUserRunItems retains scalar output on its originating execution', () => {
  const items = buildUserRunItems({
    terminalEntries: [{
      id: 'scalar-run',
      kind: 'output',
      source: 'analysis',
      origin: 'user',
      label: 'Selection run',
      command: 'total = 42\ntotal',
      runId: 'run-scalar',
      status: 'success',
      scalarOutputs: [{ name: 'total', value: 42, runId: 'run-scalar', result_type: 'int' }],
    }],
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].code, 'total = 42\ntotal')
  assert.equal(items[0].scalarOutputs.length, 1)
  assert.equal(items[0].scalarOutputs[0].value, 42)
  assert.equal(items[0].scalarOutputs[0].type, 'int')
})

test('buildUserRunItems excludes AI execution logs from the manual Runs feed', () => {
  const items = buildUserRunItems({
    terminalEntries: [{
      id: 'ai-run',
      kind: 'output',
      source: 'analysis',
      origin: 'ai',
      label: 'Run output',
      command: 'conversion_rate = converted / total',
      stdout: '0.42',
    }],
  })

  assert.equal(items.length, 0)
})
