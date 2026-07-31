import { computed, ref } from 'vue'

import type { SchemaHubColumn, SchemaHubSelection, SchemaHubTable } from '../types/schemaHub'

type NativeRecord = Record<string, unknown>

function asRecord(value: unknown): NativeRecord {
  return value && typeof value === 'object' ? value as NativeRecord : {}
}

export function normalizeAliasList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((alias) => String(alias).trim()).filter(Boolean)
  if (typeof value === 'string') {
    return value.split(',').map((alias) => alias.trim()).filter(Boolean)
  }
  return []
}

export function normalizeSchemaColumns(
  tableId: string,
  tableName: string,
  values: unknown,
): SchemaHubColumn[] {
  if (!Array.isArray(values)) return []
  return values.map((value) => {
    const column = asRecord(value)
    return {
      name: String(column.name || column.column_name || '').trim(),
      dataType: String(column.dtype || column.type || 'VARCHAR').trim(),
      nullable: Boolean(column.nullable),
      description: String(column.description || ''),
      aliases: normalizeAliasList(column.aliases),
      tableId,
      tableName,
    }
  }).filter((column) => column.name)
}

export function normalizeSchemaTables(datasets: unknown, schemas: unknown): SchemaHubTable[] {
  if (!Array.isArray(datasets)) return []
  const schemaByName = new Map(
    (Array.isArray(schemas) ? schemas : []).map((value) => {
      const schema = asRecord(value)
      return [String(schema.table_name || '').trim(), schema]
    }),
  )

  return datasets.map((value) => {
    const dataset = asRecord(value)
    const tableName = String(dataset.table_name || dataset.name || '').trim()
    const tableId = String(dataset.id || `table:${tableName}`).trim()
    const schema = schemaByName.get(tableName) || {}
    return {
      id: tableId,
      tableName,
      tableContext: String(schema.table_context || ''),
      rowCount: Number(dataset.row_count || 0),
      status: String(dataset.schema_status || ''),
      columns: normalizeSchemaColumns(tableId, tableName, schema.columns),
    }
  }).filter((table) => table.tableName).sort((left, right) => left.tableName.localeCompare(right.tableName))
}

export function useSchemaHubState() {
  const tables = ref<SchemaHubTable[]>([])
  const savedColumns = new Map<string, SchemaHubColumn[]>()
  const selection = ref<SchemaHubSelection>({ kind: 'workspace' })
  const dirtyTableIds = ref(new Set<string>())
  const isLoading = ref(false)
  const loadError = ref('')
  let activeLoad = 0

  const selectedTable = computed(() => {
    if (selection.value.kind !== 'table') return null
    const tableId = selection.value.tableId
    return tables.value.find((table) => table.id === tableId) || null
  })
  const isEdited = computed(() => dirtyTableIds.value.size > 0)

  function beginLoad() {
    activeLoad += 1
    isLoading.value = true
    loadError.value = ''
    return activeLoad
  }

  function applyLoad(loadId: number, nextTables: SchemaHubTable[]) {
    if (loadId !== activeLoad) return false
    tables.value = nextTables
    savedColumns.clear()
    nextTables.forEach((table) => savedColumns.set(table.id, cloneColumns(table.columns)))
    if (selection.value.kind === 'table') {
      const tableId = selection.value.tableId
      if (!nextTables.some((table) => table.id === tableId)) {
        selection.value = { kind: 'workspace' }
      }
    }
    dirtyTableIds.value = new Set()
    isLoading.value = false
    return true
  }

  function rejectLoad(loadId: number, error: unknown) {
    if (loadId !== activeLoad) return false
    loadError.value = error instanceof Error ? error.message : String(error || '')
    isLoading.value = false
    return true
  }

  function clear() {
    activeLoad += 1
    tables.value = []
    savedColumns.clear()
    selection.value = { kind: 'workspace' }
    dirtyTableIds.value = new Set()
    isLoading.value = false
    loadError.value = ''
  }

  function markTableDirty(tableId: string) {
    dirtyTableIds.value = new Set(dirtyTableIds.value).add(tableId)
  }

  function selectWorkspace() {
    selection.value = { kind: 'workspace' }
  }

  function selectTable(tableId: string) {
    if (!tables.value.some((table) => table.id === tableId)) return false
    selection.value = { kind: 'table', tableId }
    return true
  }

  function clearDirtyTables() {
    tables.value.forEach((table) => savedColumns.set(table.id, cloneColumns(table.columns)))
    dirtyTableIds.value = new Set()
  }

  function clearTableDirty(tableId: string) {
    const table = tables.value.find((candidate) => candidate.id === tableId)
    if (table) savedColumns.set(tableId, cloneColumns(table.columns))
    const next = new Set(dirtyTableIds.value)
    next.delete(tableId)
    dirtyTableIds.value = next
  }

  function replaceTableColumns(tableId: string, columns: SchemaHubColumn[]) {
    tables.value = tables.value.map((table) => table.id === tableId ? { ...table, columns } : table)
  }

  function replaceTableContext(tableId: string, tableContext: string) {
    tables.value = tables.value.map((table) => table.id === tableId ? { ...table, tableContext } : table)
  }

  function resetTable(tableId: string) {
    const columns = savedColumns.get(tableId)
    if (!columns) return false
    replaceTableColumns(tableId, cloneColumns(columns))
    const next = new Set(dirtyTableIds.value)
    next.delete(tableId)
    dirtyTableIds.value = next
    return true
  }

  return {
    tables,
    selection,
    selectedTable,
    dirtyTableIds,
    isEdited,
    isLoading,
    loadError,
    beginLoad,
    applyLoad,
    rejectLoad,
    clear,
    selectWorkspace,
    selectTable,
    markTableDirty,
    clearDirtyTables,
    clearTableDirty,
    replaceTableColumns,
    replaceTableContext,
    resetTable,
  }
}

function cloneColumns(columns: SchemaHubColumn[]) {
  return columns.map((column) => ({ ...column, aliases: [...column.aliases] }))
}
