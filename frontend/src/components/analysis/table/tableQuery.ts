export const DEFAULT_TABLE_PAGE_SIZE = 100

export type TableFilterKind = 'text' | 'number' | 'boolean'
export type TableSortDirection = 'asc' | 'desc'

export interface TableSort {
  columnId: string
  direction: TableSortDirection
}

export interface TableFilter {
  columnId: string
  kind: TableFilterKind
  operator: string
  value?: unknown
  valueTo?: unknown
}

export interface TableQuery {
  pageIndex: number
  pageSize: number
  sorting: TableSort[]
  filters: TableFilter[]
}

export interface TanStackSort {
  id: string
  desc: boolean
}

export interface TanStackColumnFilter {
  id: string
  value: Omit<TableFilter, 'columnId'>
}

export interface FilterOperator {
  value: string
  label: string
}

interface TableFilterRow {
  getValue(columnId: string): unknown
  getAllCells(): Array<{ getValue(): unknown }>
}

const VALUELESS_FILTER_OPERATORS = new Set(['blank', 'notBlank'])

export function createTableQuery(overrides: Partial<TableQuery> = {}): TableQuery {
  const pageIndex = Number(overrides.pageIndex || 0)
  const pageSize = Number(overrides.pageSize || DEFAULT_TABLE_PAGE_SIZE)
  return {
    pageIndex: Number.isFinite(pageIndex) ? Math.max(0, Math.trunc(pageIndex)) : 0,
    pageSize: Number.isFinite(pageSize) ? Math.max(1, Math.trunc(pageSize)) : DEFAULT_TABLE_PAGE_SIZE,
    sorting: Array.isArray(overrides.sorting) ? overrides.sorting : [],
    filters: Array.isArray(overrides.filters) ? overrides.filters : [],
  }
}

export function resolveTableStateUpdater<Value>(
  updater: Value | ((currentValue: Value) => Value),
  currentValue: Value,
): Value {
  return typeof updater === 'function'
    ? (updater as (value: Value) => Value)(currentValue)
    : updater
}

export function toTanStackSorting(sorting: unknown): TanStackSort[] {
  return (Array.isArray(sorting) ? sorting : []).map((entry) => ({
    id: String((entry as Partial<TableSort>)?.columnId || ''),
    desc: (entry as Partial<TableSort>)?.direction === 'desc',
  })).filter((entry) => entry.id)
}

export function fromTanStackSorting(sorting: unknown): TableSort[] {
  return (Array.isArray(sorting) ? sorting : []).map((entry) => ({
    columnId: String((entry as Partial<TanStackSort>)?.id || ''),
    direction: (entry as Partial<TanStackSort>)?.desc ? 'desc' as const : 'asc' as const,
  })).filter((entry) => entry.columnId)
}

export function toTanStackColumnFilters(filters: unknown): TanStackColumnFilter[] {
  return (Array.isArray(filters) ? filters : []).map((entry) => ({
    id: String((entry as Partial<TableFilter>)?.columnId || ''),
    value: {
      kind: normalizeFilterKind((entry as Partial<TableFilter>)?.kind),
      operator: String((entry as Partial<TableFilter>)?.operator || 'contains'),
      value: (entry as Partial<TableFilter>)?.value ?? '',
      valueTo: (entry as Partial<TableFilter>)?.valueTo ?? '',
    },
  })).filter((entry) => entry.id)
}

export function inferTableFilterKind(rows: unknown, columnId: string): TableFilterKind {
  const sourceRows = Array.isArray(rows) ? rows : []
  for (const row of sourceRows) {
    const value = row && typeof row === 'object'
      ? (row as Record<string, unknown>)[columnId]
      : undefined
    if (value == null || value === '') continue
    if (typeof value === 'boolean') return 'boolean'
    if (typeof value === 'number' && Number.isFinite(value)) return 'number'
    return 'text'
  }
  return 'text'
}

export function getFilterOperators(kind: TableFilterKind): FilterOperator[] {
  if (kind === 'number') {
    return [
      { value: 'equals', label: 'Equals' },
      { value: 'notEqual', label: 'Does not equal' },
      { value: 'greaterThan', label: 'Greater than' },
      { value: 'greaterThanOrEqual', label: 'Greater than or equal' },
      { value: 'lessThan', label: 'Less than' },
      { value: 'lessThanOrEqual', label: 'Less than or equal' },
      { value: 'inRange', label: 'In range' },
      { value: 'blank', label: 'Is blank' },
      { value: 'notBlank', label: 'Is not blank' },
    ]
  }
  if (kind === 'boolean') {
    return [
      { value: 'equals', label: 'Equals' },
      { value: 'blank', label: 'Is blank' },
      { value: 'notBlank', label: 'Is not blank' },
    ]
  }
  return [
    { value: 'contains', label: 'Contains' },
    { value: 'notContains', label: 'Does not contain' },
    { value: 'equals', label: 'Equals' },
    { value: 'notEqual', label: 'Does not equal' },
    { value: 'startsWith', label: 'Starts with' },
    { value: 'endsWith', label: 'Ends with' },
    { value: 'blank', label: 'Is blank' },
    { value: 'notBlank', label: 'Is not blank' },
  ]
}

export function isValuelessFilterOperator(operator: unknown): boolean {
  return VALUELESS_FILTER_OPERATORS.has(String(operator || ''))
}

export function isCompleteTableFilter(filter: Partial<TableFilter> | null | undefined): boolean {
  const operator = String(filter?.operator || '')
  if (isValuelessFilterOperator(operator)) return true
  if (filter?.kind === 'boolean') return filter?.value === true || filter?.value === false
  if (filter?.kind === 'number') {
    if (String(filter?.value ?? '').trim() === '') return false
    if (!Number.isFinite(Number(filter?.value))) return false
    if (operator === 'inRange') {
      if (String(filter?.valueTo ?? '').trim() === '') return false
      return Number.isFinite(Number(filter?.valueTo))
    }
    return true
  }
  return String(filter?.value ?? '').length > 0
}

export function toBackendSortModel(query: Partial<TableQuery> | null | undefined) {
  return (Array.isArray(query?.sorting) ? query.sorting : []).map((entry) => ({
    colId: String(entry?.columnId || ''),
    sort: entry?.direction === 'desc' ? 'desc' : 'asc',
  })).filter((entry) => entry.colId)
}

export function toBackendFilterModel(
  query: Partial<TableQuery> | null | undefined,
): Record<string, Record<string, unknown>> {
  const model: Record<string, Record<string, unknown>> = {}
  for (const entry of Array.isArray(query?.filters) ? query.filters : []) {
    const columnId = String(entry?.columnId || '')
    if (!columnId || !isCompleteTableFilter(entry)) continue
    const kind = normalizeFilterKind(entry?.kind)
    const filter: Record<string, unknown> = {
      filterType: kind,
      type: String(entry?.operator || defaultFilterOperator(kind)),
    }
    if (!isValuelessFilterOperator(filter.type)) {
      filter.filter = normalizeFilterValue(kind, entry?.value)
      if (filter.type === 'inRange') {
        filter.filterTo = normalizeFilterValue(kind, entry?.valueTo)
      }
    }
    model[columnId] = filter
  }
  return model
}

export function tableColumnFilter(
  row: TableFilterRow,
  columnId: string,
  filterValue: Partial<Omit<TableFilter, 'columnId'>> | null | undefined,
): boolean {
  const filter: TableFilter = {
    columnId,
    kind: normalizeFilterKind(filterValue?.kind),
    operator: String(filterValue?.operator || 'contains'),
    value: filterValue?.value,
    valueTo: filterValue?.valueTo,
  }
  if (!isCompleteTableFilter(filter)) return true

  const rawValue = row.getValue(columnId)
  const isBlank = rawValue == null || String(rawValue) === ''
  if (filter.operator === 'blank') return isBlank
  if (filter.operator === 'notBlank') return !isBlank
  if (isBlank) return filter.operator === 'notEqual' || filter.operator === 'notContains'

  if (filter.kind === 'boolean') {
    return Boolean(rawValue) === Boolean(filter.value)
  }
  if (filter.kind === 'number') {
    const value = Number(rawValue)
    const target = Number(filter.value)
    const targetTo = Number(filter.valueTo)
    if (!Number.isFinite(value) || !Number.isFinite(target)) return false
    if (filter.operator === 'notEqual') return value !== target
    if (filter.operator === 'greaterThan') return value > target
    if (filter.operator === 'greaterThanOrEqual') return value >= target
    if (filter.operator === 'lessThan') return value < target
    if (filter.operator === 'lessThanOrEqual') return value <= target
    if (filter.operator === 'inRange') {
      const low = Math.min(target, targetTo)
      const high = Math.max(target, targetTo)
      return value >= low && value <= high
    }
    return value === target
  }

  const value = String(rawValue).toLocaleLowerCase()
  const target = String(filter.value ?? '').toLocaleLowerCase()
  if (filter.operator === 'notContains') return !value.includes(target)
  if (filter.operator === 'equals') return value === target
  if (filter.operator === 'notEqual') return value !== target
  if (filter.operator === 'startsWith') return value.startsWith(target)
  if (filter.operator === 'endsWith') return value.endsWith(target)
  return value.includes(target)
}

export function tableGlobalFilter(
  row: TableFilterRow,
  _columnId: string,
  filterValue: unknown,
): boolean {
  const needle = String(filterValue || '').trim().toLocaleLowerCase()
  if (!needle) return true
  return row.getAllCells().some((cell) => {
    const value = cell.getValue()
    return value != null && String(value).toLocaleLowerCase().includes(needle)
  })
}

function normalizeFilterKind(kind: unknown): TableFilterKind {
  if (kind === 'number' || kind === 'boolean') return kind
  return 'text'
}

function defaultFilterOperator(kind: TableFilterKind): string {
  if (kind === 'boolean' || kind === 'number') return 'equals'
  return 'contains'
}

function normalizeFilterValue(kind: TableFilterKind, value: unknown): unknown {
  if (kind === 'number') return Number(value)
  if (kind === 'boolean') return value === true || String(value).toLowerCase() === 'true'
  return String(value ?? '')
}
