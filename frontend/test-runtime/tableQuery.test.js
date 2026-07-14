import { describe, expect, it } from 'vitest'

import {
  createTableQuery,
  fromTanStackSorting,
  inferTableFilterKind,
  isCompleteTableFilter,
  toBackendFilterModel,
  toBackendSortModel,
  toTanStackSorting,
} from '../src/components/analysis/table/tableQuery'

describe('table query adapter', () => {
  it('keeps application query state independent from TanStack and backend shapes', () => {
    const query = createTableQuery({
      pageIndex: 2,
      sorting: [
        { columnId: 'revenue.total', direction: 'desc' },
        { columnId: 'region', direction: 'asc' },
      ],
    })

    expect(toTanStackSorting(query.sorting)).toEqual([
      { id: 'revenue.total', desc: true },
      { id: 'region', desc: false },
    ])
    expect(fromTanStackSorting(toTanStackSorting(query.sorting))).toEqual(query.sorting)
    expect(toBackendSortModel(query)).toEqual([
      { colId: 'revenue.total', sort: 'desc' },
      { colId: 'region', sort: 'asc' },
    ])
  })

  it('converts supported text, numeric, boolean, and blank filters for the existing API', () => {
    const query = createTableQuery({
      filters: [
        { columnId: 'name', kind: 'text', operator: 'contains', value: 'Ada' },
        { columnId: 'score', kind: 'number', operator: 'inRange', value: '10', valueTo: '20' },
        { columnId: 'active', kind: 'boolean', operator: 'equals', value: false },
        { columnId: 'notes', kind: 'text', operator: 'blank', value: '' },
        { columnId: 'ignored', kind: 'text', operator: 'contains', value: '' },
      ],
    })

    expect(toBackendFilterModel(query)).toEqual({
      name: { filterType: 'text', type: 'contains', filter: 'Ada' },
      score: { filterType: 'number', type: 'inRange', filter: 10, filterTo: 20 },
      active: { filterType: 'boolean', type: 'equals', filter: false },
      notes: { filterType: 'text', type: 'blank' },
    })
  })

  it('infers only stable primitive filter kinds from loaded rows', () => {
    expect(inferTableFilterKind([{ value: null }, { value: 42 }], 'value')).toBe('number')
    expect(inferTableFilterKind([{ value: true }], 'value')).toBe('boolean')
    expect(inferTableFilterKind([{ value: '2026-01-01' }], 'value')).toBe('text')
  })

  it('rejects empty numeric filters and normalizes invalid pagination input', () => {
    expect(isCompleteTableFilter({ kind: 'number', operator: 'equals', value: '' })).toBe(false)
    expect(isCompleteTableFilter({ kind: 'number', operator: 'inRange', value: '1', valueTo: '' })).toBe(false)
    expect(createTableQuery({ pageIndex: 'invalid', pageSize: Number.NaN })).toMatchObject({
      pageIndex: 0,
      pageSize: 100,
    })
  })
})
