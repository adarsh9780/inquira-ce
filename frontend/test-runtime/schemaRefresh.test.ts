import { describe, expect, it } from 'vitest'

import { normalizeSchemaRefreshResult, schemaRefreshFeedback } from '../src/utils/schemaRefresh'

describe('schema refresh feedback', () => {
  it('normalizes native counts and reports partial source failures', () => {
    const result = normalizeSchemaRefreshResult({
      attempted: 3,
      succeeded: 2,
      changed: 9,
      failures: [{ connection_name: 'Legacy CSV', message: 'Could not inspect the source.' }],
    })

    expect(result).toMatchObject({ attempted: 3, succeeded: 2, changed: 2 })
    expect(schemaRefreshFeedback(result)).toEqual({
      type: 'warning',
      title: 'Schema partially refreshed',
      message: '2 of 3 data sources refreshed. Check Legacy CSV.',
    })
  })

  it('distinguishes empty, unchanged, and changed workspaces', () => {
    expect(schemaRefreshFeedback(normalizeSchemaRefreshResult({})).type).toBe('info')
    expect(schemaRefreshFeedback(normalizeSchemaRefreshResult({ attempted: 2, succeeded: 2 })).title).toBe('Schema is up to date')
    expect(schemaRefreshFeedback(normalizeSchemaRefreshResult({ attempted: 2, succeeded: 2, changed: 1 })).title).toBe('Schema refreshed')
  })
})
