export const DEFAULT_TABLE_PAGE_SIZE = 100

const VALUELESS_FILTER_OPERATORS = new Set(['blank', 'notBlank'])

export function createTableQuery(overrides = {}) {
  const pageIndex = Number(overrides.pageIndex || 0)
  const pageSize = Number(overrides.pageSize || DEFAULT_TABLE_PAGE_SIZE)
  return {
    pageIndex: Number.isFinite(pageIndex) ? Math.max(0, Math.trunc(pageIndex)) : 0,
    pageSize: Number.isFinite(pageSize) ? Math.max(1, Math.trunc(pageSize)) : DEFAULT_TABLE_PAGE_SIZE,
    sorting: Array.isArray(overrides.sorting) ? overrides.sorting : [],
    filters: Array.isArray(overrides.filters) ? overrides.filters : [],
  }
}

export function resolveTableStateUpdater(updater, currentValue) {
  return typeof updater === 'function' ? updater(currentValue) : updater
}

export function toTanStackSorting(sorting) {
  return (Array.isArray(sorting) ? sorting : []).map((entry) => ({
    id: String(entry?.columnId || ''),
    desc: entry?.direction === 'desc',
  })).filter((entry) => entry.id)
}

export function fromTanStackSorting(sorting) {
  return (Array.isArray(sorting) ? sorting : []).map((entry) => ({
    columnId: String(entry?.id || ''),
    direction: entry?.desc ? 'desc' : 'asc',
  })).filter((entry) => entry.columnId)
}

export function toTanStackColumnFilters(filters) {
  return (Array.isArray(filters) ? filters : []).map((entry) => ({
    id: String(entry?.columnId || ''),
    value: {
      kind: normalizeFilterKind(entry?.kind),
      operator: String(entry?.operator || 'contains'),
      value: entry?.value ?? '',
      valueTo: entry?.valueTo ?? '',
    },
  })).filter((entry) => entry.id)
}

export function inferTableFilterKind(rows, columnId) {
  const sourceRows = Array.isArray(rows) ? rows : []
  for (const row of sourceRows) {
    const value = row?.[columnId]
    if (value == null || value === '') continue
    if (typeof value === 'boolean') return 'boolean'
    if (typeof value === 'number' && Number.isFinite(value)) return 'number'
    return 'text'
  }
  return 'text'
}

export function getFilterOperators(kind) {
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

export function isValuelessFilterOperator(operator) {
  return VALUELESS_FILTER_OPERATORS.has(String(operator || ''))
}

export function isCompleteTableFilter(filter) {
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

export function toBackendSortModel(query) {
  return (Array.isArray(query?.sorting) ? query.sorting : []).map((entry) => ({
    colId: String(entry?.columnId || ''),
    sort: entry?.direction === 'desc' ? 'desc' : 'asc',
  })).filter((entry) => entry.colId)
}

export function toBackendFilterModel(query) {
  const model = {}
  for (const entry of Array.isArray(query?.filters) ? query.filters : []) {
    const columnId = String(entry?.columnId || '')
    if (!columnId || !isCompleteTableFilter(entry)) continue
    const kind = normalizeFilterKind(entry?.kind)
    const filter = {
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

export function tableColumnFilter(row, columnId, filterValue) {
  const filter = {
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

export function tableGlobalFilter(row, _columnId, filterValue) {
  const needle = String(filterValue || '').trim().toLocaleLowerCase()
  if (!needle) return true
  return row.getAllCells().some((cell) => {
    const value = cell.getValue()
    return value != null && String(value).toLocaleLowerCase().includes(needle)
  })
}

function normalizeFilterKind(kind) {
  if (kind === 'number' || kind === 'boolean') return kind
  return 'text'
}

function defaultFilterOperator(kind) {
  if (kind === 'boolean' || kind === 'number') return 'equals'
  return 'contains'
}

function normalizeFilterValue(kind, value) {
  if (kind === 'number') return Number(value)
  if (kind === 'boolean') return value === true || String(value).toLowerCase() === 'true'
  return String(value ?? '')
}
