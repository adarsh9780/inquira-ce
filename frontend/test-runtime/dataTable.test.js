import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import DataTable from '../src/components/analysis/table/DataTable.vue'
import { createTableQuery } from '../src/components/analysis/table/tableQuery'

function rows(count) {
  return Array.from({ length: count }, (_, index) => ({
    name: `Row ${String(index + 1).padStart(3, '0')}`,
    score: index + 1,
  }))
}

describe('DataTable', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    vi.unstubAllGlobals()
  })

  it('paginates client rows in 100-row pages and emits neutral page state', async () => {
    const wrapper = mount(DataTable, {
      attachTo: document.body,
      props: {
        rows: rows(205),
        columns: ['name', 'score'],
        rowCount: 205,
        query: createTableQuery(),
      },
    })

    expect(wrapper.findAll('tbody tr')).toHaveLength(100)
    expect(wrapper.text()).toContain('1–100 of 205')
    await wrapper.get('button[aria-label="Next page"]').trigger('click')
    expect(wrapper.emitted('update:query')?.at(-1)?.[0]).toMatchObject({ pageIndex: 1, pageSize: 100 })

    await wrapper.setProps({ query: createTableQuery({ pageIndex: 1 }) })
    expect(wrapper.text()).toContain('101–200 of 205')
  })

  it('emits sorting and filtering without leaking TanStack state to the parent', async () => {
    const wrapper = mount(DataTable, {
      attachTo: document.body,
      props: {
        rows: rows(3),
        columns: ['name', 'score'],
        rowCount: 3,
        query: createTableQuery(),
        manual: true,
      },
    })

    await wrapper.get('button[aria-label="Sort score ascending"]').trigger('click')
    expect(wrapper.emitted('update:query')?.at(-1)?.[0]).toMatchObject({
      pageIndex: 0,
      sorting: [{ columnId: 'score', direction: 'asc' }],
    })

    await wrapper.get('button[aria-label="Filter name"]').trigger('click')
    const menu = document.body.querySelector('[role="dialog"][aria-label="Filter name"]')
    expect(menu).toBeTruthy()
    const input = menu.querySelector('input')
    input.value = 'Row 002'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    menu.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:query')?.at(-1)?.[0]).toMatchObject({
      pageIndex: 0,
      filters: [{ columnId: 'name', kind: 'text', operator: 'contains', value: 'Row 002' }],
    })
  })

  it('filters live rows locally and copies the focused cell value', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(DataTable, {
      attachTo: document.body,
      props: {
        rows: rows(3),
        columns: ['name', 'score'],
        rowCount: 3,
        globalFilter: '002',
        query: createTableQuery({
          filters: [{ columnId: 'score', kind: 'number', operator: 'greaterThan', value: 1 }],
        }),
      },
    })

    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('Row 002')
    const cell = wrapper.get('tbody td')
    await cell.trigger('keydown', { key: 'c', ctrlKey: true })
    expect(writeText).toHaveBeenCalledWith('Row 002')
  })

  it('keeps the grid visible when a query has no matching rows', () => {
    const wrapper = mount(DataTable, {
      props: {
        rows: [],
        columns: ['name', 'score'],
        rowCount: 0,
        query: createTableQuery(),
        manual: true,
      },
    })

    expect(wrapper.get('[role="grid"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('No matching rows')
    expect(wrapper.text()).toContain('0 of 0')
  })
})
