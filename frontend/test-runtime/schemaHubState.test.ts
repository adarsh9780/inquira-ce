import { describe, expect, it } from 'vitest'

import {
  normalizeAliasList,
  normalizeSchemaTables,
  useSchemaHubState,
} from '../src/composables/useSchemaHubState'

describe('schema hub state', () => {
  it('normalizes native datasets into stable typed tables', () => {
    const tables = normalizeSchemaTables(
      [
        { id: 'table-orders', table_name: 'orders', row_count: 12, schema_status: 'ready' },
        { id: 'table-customers', table_name: 'customers', row_count: 4 },
      ],
      [
        {
          table_name: 'orders',
          table_context: 'One row per completed order.',
          columns: [
            { name: 'order_id', dtype: 'BIGINT', nullable: false, aliases: 'id, order number' },
          ],
        },
        { table_name: 'customers', columns: [] },
      ],
    )

    expect(tables.map((table) => table.id)).toEqual(['table-customers', 'table-orders'])
    expect(tables[1]?.tableContext).toBe('One row per completed order.')
    expect(tables[1]?.columns[0]).toMatchObject({
      name: 'order_id',
      dataType: 'BIGINT',
      aliases: ['id', 'order number'],
      tableId: 'table-orders',
      tableName: 'orders',
    })
    expect(normalizeAliasList([' primary ', '', 'legacy'])).toEqual(['primary', 'legacy'])
  })

  it('ignores stale loads and resets a missing table selection', () => {
    const state = useSchemaHubState()
    const staleLoad = state.beginLoad()
    const currentLoad = state.beginLoad()
    const tables = normalizeSchemaTables([{ id: 'orders', table_name: 'orders' }], [])

    expect(state.applyLoad(staleLoad, tables)).toBe(false)
    expect(state.tables.value).toEqual([])
    expect(state.applyLoad(currentLoad, tables)).toBe(true)

    expect(state.selectTable('orders')).toBe(true)
    expect(state.selectTable('missing')).toBe(false)
    expect(state.selectedTable.value?.tableName).toBe('orders')
    const reload = state.beginLoad()
    state.applyLoad(reload, [])
    expect(state.selection.value).toEqual({ kind: 'workspace' })
  })

  it('tracks dirty tables by stable identity', () => {
    const state = useSchemaHubState()

    state.markTableDirty('table-orders')
    state.markTableDirty('table-customers')
    expect(state.isEdited.value).toBe(true)
    expect([...state.dirtyTableIds.value]).toEqual(['table-orders', 'table-customers'])

    state.clearTableDirty('table-orders')
    expect([...state.dirtyTableIds.value]).toEqual(['table-customers'])
    state.clearDirtyTables()
    expect(state.isEdited.value).toBe(false)
  })

  it('selects the data-source surface independently of tables', () => {
    const state = useSchemaHubState()
    state.selectSources()
    expect(state.selection.value).toEqual({ kind: 'sources' })
    expect(state.selectedTable.value).toBeNull()
  })

  it('restores the last saved columns when table edits are discarded', () => {
    const state = useSchemaHubState()
    const load = state.beginLoad()
    const tables = normalizeSchemaTables(
      [{ id: 'table-orders', table_name: 'orders' }],
      [{ table_name: 'orders', columns: [{ name: 'order_id', description: 'Original' }] }],
    )
    state.applyLoad(load, tables)

    state.replaceTableColumns('table-orders', [{ ...tables[0]!.columns[0]!, description: 'Draft' }])
    state.markTableDirty('table-orders')
    expect(state.resetTable('table-orders')).toBe(true)
    expect(state.tables.value[0]?.columns[0]?.description).toBe('Original')
    expect(state.dirtyTableIds.value.has('table-orders')).toBe(false)

    const savedColumns = [{ ...state.tables.value[0]!.columns[0]!, description: 'Saved' }]
    state.replaceTableColumns('table-orders', savedColumns)
    state.markTableDirty('table-orders')
    state.clearTableDirty('table-orders')
    state.replaceTableColumns('table-orders', [{ ...savedColumns[0]!, description: 'Another draft' }])
    state.markTableDirty('table-orders')
    state.resetTable('table-orders')
    expect(state.tables.value[0]?.columns[0]?.description).toBe('Saved')
  })

  it('replaces table context without marking column metadata dirty', () => {
    const state = useSchemaHubState()
    const load = state.beginLoad()
    state.applyLoad(load, normalizeSchemaTables(
      [{ id: 'table-orders', table_name: 'orders' }],
      [{ table_name: 'orders', table_context: 'Original context', columns: [] }],
    ))

    state.replaceTableContext('table-orders', 'Updated context')

    expect(state.tables.value[0]?.tableContext).toBe('Updated context')
    expect(state.isEdited.value).toBe(false)
  })
})
