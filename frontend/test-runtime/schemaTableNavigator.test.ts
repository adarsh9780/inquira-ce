import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SchemaTableNavigator from '../src/components/schema/SchemaTableNavigator.vue'
import type { SchemaHubTable } from '../src/types/schemaHub'

const tables: SchemaHubTable[] = [{
  id: 'orders',
  tableName: 'orders',
  rowCount: 1200,
  status: 'ready',
  columns: [],
}]

describe('SchemaTableNavigator', () => {
  it('shows workspace and table destinations with dirty state', async () => {
    const wrapper = mount(SchemaTableNavigator, {
      props: {
        tables,
        selection: { kind: 'table', tableId: 'orders' },
        dirtyTableIds: new Set(['orders']),
      },
    })

    expect(wrapper.text()).toContain('Workspace context')
    expect(wrapper.text()).toContain('1,200 rows')
    expect(wrapper.get('[aria-label="Unsaved changes"]').exists()).toBe(true)
    expect(wrapper.get('button[aria-current="page"]').text()).toContain('orders')

    await wrapper.findAll('button')[0]!.trigger('click')
    expect(wrapper.emitted('select')).toEqual([[{ kind: 'workspace' }]])
  })
})
