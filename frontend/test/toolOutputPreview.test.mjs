import test from 'node:test'
import assert from 'node:assert/strict'
import { buildToolOutputPreview } from '../src/utils/toolOutputPreview.js'

test('tool output preview detects code languages', () => {
  assert.equal(buildToolOutputPreview({ output: 'print("ok")' }).kind, 'code-python')
  assert.equal(buildToolOutputPreview({ output: 'select * from sales limit 5' }).kind, 'code-sql')
  assert.equal(buildToolOutputPreview({ output: 'uv run pytest agents/tests' }).kind, 'code-bash')
})

test('tool output preview detects markdown tables and structured tables', () => {
  const markdown = buildToolOutputPreview({ output: '| A | B |\n|---|---|\n| 1 | 2 |' })
  assert.equal(markdown.kind, 'markdown')

  const table = buildToolOutputPreview({
    output: {
      columns: ['name', 'score'],
      rows: [{ name: 'A', score: 1 }],
      row_count: 1,
    },
  })
  assert.equal(table.kind, 'table')
  assert.deepEqual(table.columns, ['name', 'score'])
  assert.deepEqual(table.rows, [['A', '1']])
})

test('tool output preview handles errors, json, and truncation', () => {
  const error = buildToolOutputPreview({ status: 'error', output: { stderr: 'Traceback\nboom' } })
  assert.equal(error.kind, 'logs')
  assert.equal(error.error, true)

  const json = buildToolOutputPreview({ output: { match_count: 2, columns: [] } })
  assert.equal(json.kind, 'json')
  assert.equal(json.summary.some((item) => item.startsWith('match_count:')), true)

  const long = buildToolOutputPreview({ output: 'x'.repeat(5000) })
  assert.equal(long.truncated, true)
})
