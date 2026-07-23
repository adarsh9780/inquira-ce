import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SegmentedControl from '../src/components/ui/SegmentedControl.vue'

describe('SegmentedControl evidence counts', () => {
  it('renders useful counts without announcing zero-value noise', async () => {
    const wrapper = mount(SegmentedControl, {
      props: {
        modelValue: 'table',
        options: [
          { value: 'table', label: 'Tables', count: 3 },
          { value: 'chart', label: 'Charts', count: 0 },
        ],
      },
    })

    expect(wrapper.get('[data-segment-count="table"]').text()).toBe('3')
    expect(wrapper.find('[data-segment-count="chart"]').exists()).toBe(false)

    await wrapper.findAll('[role="tab"]')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['chart'])
  })
})
