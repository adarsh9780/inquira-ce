import { describe, expect, it } from 'vitest'

import { buildToolOutputPreview } from '../src/utils/toolOutputPreview'

describe('tool output previews', () => {
  it('detects code languages', () => {
    expect(buildToolOutputPreview({ output: 'print("ok")' }).kind).toBe('code-python')
    expect(buildToolOutputPreview({ output: 'select * from sales limit 5' }).kind).toBe('code-sql')
    expect(buildToolOutputPreview({ output: 'uv run pytest agents/tests' }).kind).toBe('code-bash')
  })

  it('detects markdown tables and structured tables', () => {
    const markdown = buildToolOutputPreview({ output: '| A | B |\n|---|---|\n| 1 | 2 |' })
    expect(markdown.kind).toBe('markdown')

    const table = buildToolOutputPreview({
      output: {
        columns: ['name', 'score'],
        rows: [{ name: 'A', score: 1 }],
        row_count: 1,
      },
    })
    expect(table.kind).toBe('table')
    expect(table.columns).toEqual(['name', 'score'])
    expect(table.rows).toEqual([['A', '1']])
  })

  it('handles errors, JSON, and truncation', () => {
    const error = buildToolOutputPreview({
      status: 'error',
      output: { stderr: 'Traceback\nboom' },
    })
    expect(error.kind).toBe('logs')
    expect(error.error).toBe(true)

    const json = buildToolOutputPreview({ output: { match_count: 2, columns: [] } })
    expect(json.kind).toBe('json')
    expect(json.summary?.some((item) => item.startsWith('match_count:'))).toBe(true)

    const long = buildToolOutputPreview({ output: 'x'.repeat(5000) })
    expect(long.truncated).toBe(true)
  })
})
