import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import RunTableOutput from '../src/components/analysis/runs/RunTableOutput.vue'

function tableRows(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    customer: index === 0 ? 'Carla' : `Customer ${index + 1}`,
    revenue: 2_400 - index,
    region: index % 2 === 0 ? 'West' : 'East',
    status: index % 3 === 0 ? null : 'Active',
  }))
}

describe('RunTableOutput', () => {
  it('renders a bounded two-axis grid with sticky context and a 100-row preview', () => {
    const wrapper = mount(RunTableOutput, {
      props: {
        output: {
          data: tableRows(120),
        },
      },
    })

    const viewport = wrapper.get('[data-run-table-scroll]')
    expect(viewport.attributes('tabindex')).toBe('0')
    expect(viewport.attributes('aria-label')).toBe('Scrollable table output')
    expect(wrapper.get('[role="grid"]').attributes('aria-rowcount')).toBe('120')
    expect(wrapper.get('[role="grid"]').attributes('aria-colcount')).toBe('5')
    expect(wrapper.findAll('tbody tr')).toHaveLength(100)
    expect(wrapper.get('thead th').classes()).toContain('run-table-sticky-column')
    expect(wrapper.get('tbody td').classes()).toContain('run-table-sticky-column')
    expect(wrapper.text()).toContain('Showing 100 of 120 rows')
    expect(wrapper.text()).toContain('5 columns')
    expect(wrapper.get('.run-table-null').text()).toBe('null')
  })
})
