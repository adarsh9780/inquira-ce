import { describe, expect, it } from 'vitest'
import { renderCode, renderMarkdown } from '../src/utils/messageRendering'

describe('shared message rendering', () => {
  it('sanitizes links and blocks raw HTML while retaining rich Markdown', () => {
    const rendered = renderMarkdown('[docs](https://example.com)\n\n<script>alert(1)</script>')

    expect(rendered).toContain('target="_blank"')
    expect(rendered).toContain('rel="noopener noreferrer"')
    expect(rendered).not.toContain('<script>')
  })

  it('highlights Python snapshots without permitting arbitrary markup', () => {
    const rendered = renderCode('value = "<script>"')

    expect(rendered).toContain('token')
    expect(rendered).not.toContain('<script>')
  })
})
