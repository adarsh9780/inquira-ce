import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import HeaderDropdown from '../src/components/ui/HeaderDropdown.vue'

function mountDropdown() {
  return mount(HeaderDropdown, {
    attachTo: document.body,
    props: {
      modelValue: 'alpha',
      ariaLabel: 'Choose model',
      options: [
        { value: 'alpha', label: 'Alpha' },
        { value: 'beta', label: 'Beta' },
      ],
    },
  })
}

describe('HeaderDropdown dismissal', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('hides immediately when another app element receives pointerdown', async () => {
    const wrapper = mountDropdown()
    await wrapper.get('button').trigger('click')
    await wrapper.vm.$nextTick()

    const outsideButton = document.createElement('button')
    outsideButton.textContent = 'Outside action'
    document.body.append(outsideButton)
    outsideButton.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(document.body.querySelector('[role="listbox"][data-state="open"]')).toBeNull()
    expect(document.body.querySelector<HTMLElement>('[role="listbox"]')?.style.visibility).toBe('hidden')
    wrapper.unmount()
  })

  it('hides immediately on Escape', async () => {
    const wrapper = mountDropdown()
    await wrapper.get('button').trigger('click')
    await wrapper.vm.$nextTick()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(document.body.querySelector('[role="listbox"][data-state="open"]')).toBeNull()
    expect(document.body.querySelector<HTMLElement>('[role="listbox"]')?.style.visibility).toBe('hidden')
    expect(document.activeElement).toBe(wrapper.get('button').element)
    wrapper.unmount()
  })
})
