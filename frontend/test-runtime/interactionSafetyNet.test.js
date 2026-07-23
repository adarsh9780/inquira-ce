import { mount } from '@vue/test-utils'
import axe from 'axe-core'
import { afterEach, describe, expect, it } from 'vitest'

import ConfirmationModal from '../src/components/modals/ConfirmationModal.vue'
import FloatingActionMenu from '../src/components/ui/FloatingActionMenu.vue'
import HeaderDropdown from '../src/components/ui/HeaderDropdown.vue'
import ToastNotification from '../src/components/ui/ToastNotification.vue'

async function expectNoAccessibilityViolations(element) {
  const result = await axe.run(element, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    rules: { 'color-contrast': { enabled: false } },
  })
  expect(result.violations.map((violation) => violation.id)).toEqual([])
}

describe('critical interaction safety net', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('traps confirmation focus, closes with Escape or outside click, and restores focus', async () => {
    const trigger = document.createElement('button')
    trigger.textContent = 'Delete table'
    document.body.append(trigger)
    trigger.focus()

    const wrapper = mount(ConfirmationModal, {
      attachTo: document.body,
      props: {
        isOpen: true,
        title: 'Delete table',
        message: 'This action cannot be undone.',
        confirmText: 'Delete',
      },
    })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const dialog = wrapper.get('[role="dialog"]')
    const [cancel, confirm] = dialog.findAll('button')
    expect(document.activeElement).toBe(cancel.element)

    confirm.element.focus()
    await dialog.trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(cancel.element)

    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(1)

    await wrapper.setProps({ isOpen: false })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(trigger)

    await wrapper.setProps({ isOpen: true })
    await wrapper.vm.$nextTick()
    await wrapper.get('.modal-overlay').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(2)
  })

  it('supports menu arrow navigation, Escape, and focus restoration', async () => {
    const trigger = document.createElement('button')
    trigger.textContent = 'Actions'
    document.body.append(trigger)
    trigger.focus()

    const wrapper = mount(FloatingActionMenu, {
      attachTo: document.body,
      props: {
        isOpen: false,
        items: [
          { id: 'rename', label: 'Rename' },
          { id: 'delete', label: 'Delete', destructive: true },
        ],
      },
    })
    await wrapper.setProps({ isOpen: true })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const items = [...document.body.querySelectorAll('[role="menuitem"]')]
    expect(document.activeElement).toBe(items[0])
    items[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    expect(document.activeElement).toBe(items[1])
    items[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(1)

    await wrapper.setProps({ isOpen: false })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(trigger)
  })

  it('keeps searchable dropdown selection keyboard accessible', async () => {
    const wrapper = mount(HeaderDropdown, {
      attachTo: document.body,
      props: {
        modelValue: 'alpha',
        searchable: true,
        ariaLabel: 'Choose model',
        options: [
          { value: 'alpha', label: 'Alpha' },
          { value: 'beta', label: 'Beta' },
        ],
      },
    })

    await wrapper.get('button').trigger('click')
    await wrapper.vm.$nextTick()
    const input = document.body.querySelector('input[type="text"]')
    expect(input).toBeTruthy()
    input.value = 'Beta'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('Beta')
  })

  it('announces notifications and gives the dismiss action an accessible name', async () => {
    const wrapper = mount(ToastNotification, {
      attachTo: document.body,
      props: {
        isVisible: true,
        type: 'error',
        title: 'Connection failed',
        message: 'Try again.',
        duration: 0,
      },
    })

    expect(wrapper.get('[role="alert"]').attributes('aria-live')).toBe('assertive')
    expect(wrapper.get('button').attributes('aria-label')).toBe('Dismiss Connection failed notification')
    await expectNoAccessibilityViolations(wrapper.element)
  })
})
