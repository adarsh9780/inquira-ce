import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import TableContextSurface from '../src/components/schema/TableContextSurface.vue'

function buttonByText(wrapper: ReturnType<typeof mount>, label: string) {
  return wrapper.findAll('button').find((button) => button.text().trim() === label)
}

describe('TableContextSurface', () => {
  it('trims and saves table context', async () => {
    const saveContext = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(TableContextSurface, {
      props: { modelValue: 'Original context', tableName: 'orders', saveContext },
    })

    await buttonByText(wrapper, 'Edit context')?.trigger('click')
    await wrapper.get('textarea').setValue('  One row per completed order.  ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(saveContext).toHaveBeenCalledWith('One row per completed order.')
    expect(wrapper.emitted('update:modelValue')).toEqual([['One row per completed order.']])
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('keeps the draft available when persistence fails', async () => {
    const wrapper = mount(TableContextSurface, {
      props: {
        modelValue: '',
        tableName: 'orders',
        saveContext: vi.fn().mockRejectedValue(new Error('Context storage is unavailable.')),
      },
    })

    await buttonByText(wrapper, 'Add context')?.trigger('click')
    await wrapper.get('textarea').setValue('Unsaved context')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Context storage is unavailable.')
    expect(wrapper.get<HTMLTextAreaElement>('textarea').element.value).toBe('Unsaved context')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('uses a compact summary and dismisses the context drawer with Escape', async () => {
    const wrapper = mount(TableContextSurface, {
      attachTo: document.body,
      props: {
        modelValue: 'One row per completed order.',
        tableName: 'orders',
        saveContext: vi.fn().mockResolvedValue(undefined),
      },
    })

    expect(wrapper.text()).toContain('One row per completed order.')
    expect(wrapper.find('textarea').exists()).toBe(false)
    await buttonByText(wrapper, 'Edit context')?.trigger('click')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('dismisses an unsaved context draft when the backdrop is clicked', async () => {
    const wrapper = mount(TableContextSurface, {
      props: { modelValue: '', tableName: 'orders', saveContext: vi.fn() },
    })

    await buttonByText(wrapper, 'Add context')?.trigger('click')
    await wrapper.get('textarea').setValue('Unsaved draft')
    await wrapper.get('[data-table-context-backdrop]').trigger('pointerdown')

    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
})
