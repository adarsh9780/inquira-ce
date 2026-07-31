import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import WorkspaceContextSurface from '../src/components/schema/WorkspaceContextSurface.vue'

function buttonByText(wrapper: ReturnType<typeof mount>, label: string) {
  return wrapper.findAll('button').find((button) => button.text().trim() === label)
}

describe('WorkspaceContextSurface', () => {
  it('trims and saves edited workspace context', async () => {
    const saveContext = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(WorkspaceContextSurface, {
      props: { modelValue: 'Original context', saveContext },
    })

    await buttonByText(wrapper, 'Edit')?.trigger('click')
    await wrapper.get('textarea').setValue('  Updated context  ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(saveContext).toHaveBeenCalledWith('Updated context')
    expect(wrapper.emitted('update:modelValue')).toEqual([['Updated context']])
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('keeps the editor open and reports a failed save', async () => {
    const wrapper = mount(WorkspaceContextSurface, {
      props: {
        modelValue: 'Original context',
        saveContext: vi.fn().mockRejectedValue(new Error('Context storage is unavailable.')),
      },
    })

    await buttonByText(wrapper, 'Edit')?.trigger('click')
    await wrapper.get('textarea').setValue('Unsaved context')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Context storage is unavailable.')
    expect(wrapper.get<HTMLTextAreaElement>('textarea').element.value).toBe('Unsaved context')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('locks editing actions while a save is in progress', async () => {
    let finishSave = () => {}
    const saveContext = vi.fn(() => new Promise<void>((resolve) => { finishSave = resolve }))
    const wrapper = mount(WorkspaceContextSurface, {
      props: { modelValue: 'Original context', saveContext },
    })

    await buttonByText(wrapper, 'Edit')?.trigger('click')
    await wrapper.get('form').trigger('submit')
    await nextTick()

    expect(buttonByText(wrapper, 'Saving…')?.attributes('disabled')).toBeDefined()
    expect(buttonByText(wrapper, 'Cancel')?.attributes('disabled')).toBeDefined()
    finishSave()
    await flushPromises()
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('cancels edits without persisting them', async () => {
    const saveContext = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(WorkspaceContextSurface, {
      props: { modelValue: 'Original context', saveContext },
    })

    await buttonByText(wrapper, 'Edit')?.trigger('click')
    await wrapper.get('textarea').setValue('Discard this')
    await buttonByText(wrapper, 'Cancel')?.trigger('click')

    expect(saveContext).not.toHaveBeenCalled()
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.text()).toContain('Original context')
  })
})
