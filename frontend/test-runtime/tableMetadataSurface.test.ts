import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TableMetadataSurface from '../src/components/schema/TableMetadataSurface.vue'
import type { SchemaHubTable } from '../src/types/schemaHub'

const table: SchemaHubTable = {
  id: 'table-orders',
  tableName: 'orders',
  rowCount: 1200,
  status: 'ready',
  columns: [{
    name: 'order_id',
    dataType: 'BIGINT',
    nullable: false,
    description: 'Order identifier',
    aliases: [],
    tableId: 'table-orders',
    tableName: 'orders',
  }],
}

function mountSurface() {
  return mount(TableMetadataSurface, {
    props: { table, dirty: false, saving: false, regenerating: false, busy: false },
  })
}

describe('TableMetadataSurface', () => {
  it('shows physical metadata and emits normalized alias edits', async () => {
    const wrapper = mountSurface()

    expect(wrapper.text()).toContain('1,200 rows')
    expect(wrapper.text()).toContain('BIGINT')
    expect(wrapper.text()).toContain('No')

    await wrapper.findAll('tbody td')[5]?.trigger('click')
    await wrapper.get('input[aria-label="Aliases for order_id"]').setValue('identifier, legacy')
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })

    const change = wrapper.emitted('change')?.[0]
    expect(change?.[0]).toBe('table-orders')
    expect((change?.[1] as SchemaHubTable['columns'])[0]?.aliases).toEqual(['identifier', 'legacy'])
  })

  it('commits an active edit when saving one table', async () => {
    const wrapper = mountSurface()

    await wrapper.findAll('tbody td')[4]?.trigger('click')
    await wrapper.get('textarea').setValue('Primary order key')
    await wrapper.get('button[type="button"]:last-child').trigger('click')

    const save = wrapper.emitted('save')?.[0]
    expect(save?.[0]).toBe('table-orders')
    expect((save?.[1] as SchemaHubTable['columns'])[0]?.description).toBe('Primary order key')

    await wrapper.findAll('button')[0]?.trigger('click')
    expect(wrapper.emitted('regenerate')).toEqual([['orders']])
  })
})
