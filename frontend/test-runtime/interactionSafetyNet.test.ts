import { mount } from '@vue/test-utils'
import axe from 'axe-core'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ConfirmationModal from '../src/components/modals/ConfirmationModal.vue'
import FloatingActionMenu from '../src/components/ui/FloatingActionMenu.vue'
import HeaderDropdown from '../src/components/ui/HeaderDropdown.vue'
import ToastNotification from '../src/components/ui/ToastNotification.vue'
import { DialogShell } from '../src/components/ui/dialog'

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

  it('traps confirmation focus, closes with Escape, ignores outside clicks, and restores focus', async () => {
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

    const dialog = document.body.querySelector('[role="alertdialog"]')
    const [cancel, confirm] = [...dialog.querySelectorAll('button')]
    expect(document.activeElement).toBe(cancel)

    confirm.focus()
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(document.activeElement).toBe(cancel)

    await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(1)

    await wrapper.setProps({ isOpen: false })
    await wrapper.vm.$nextTick()
    await vi.waitFor(() => expect(document.activeElement).toBe(trigger))

    await wrapper.setProps({ isOpen: true })
    await wrapper.vm.$nextTick()
    document.body.querySelector('.modal-overlay').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('submits a destructive confirmation before the dialog clears its target', async () => {
    const events = []
    const wrapper = mount(ConfirmationModal, {
      attachTo: document.body,
      props: {
        isOpen: true,
        title: 'Delete conversation',
        message: 'This action cannot be undone.',
        confirmText: 'Delete',
        onConfirm: () => events.push('confirm'),
        onClose: () => events.push('close'),
      },
    })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const buttons = [...document.body.querySelectorAll('[role="alertdialog"] button')]
    buttons.at(-1).click()
    await wrapper.vm.$nextTick()

    expect(events).toEqual(['confirm', 'close'])
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

  it('limits unopened model results and emits a Reka combobox selection', async () => {
    const wrapper = mount(HeaderDropdown, {
      attachTo: document.body,
      props: {
        modelValue: 'alpha',
        searchable: true,
        maxOptionsWithoutSearch: 1,
        ariaLabel: 'Choose model',
        options: [
          { value: 'alpha', label: 'Alpha', provider: 'openai' },
          { value: 'beta', label: 'Beta', provider: 'google' },
        ],
      },
    })

    await wrapper.get('button').trigger('click')
    await wrapper.vm.$nextTick()
    expect(document.body.querySelectorAll('[role="option"]')).toHaveLength(1)

    const input = document.body.querySelector('input')
    input.value = 'Beta'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await wrapper.vm.$nextTick()
    document.body.querySelector('[role="option"]').dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['beta'])
  })

  it('positions the model menu from the rendered trigger element', async () => {
    const wrapper = mount(HeaderDropdown, {
      attachTo: document.body,
      props: {
        modelValue: 'alpha',
        searchable: true,
        dropdownMinWidth: 288,
        ariaLabel: 'Choose model',
        options: [
          { value: 'alpha', label: 'Alpha' },
          { value: 'beta', label: 'Beta' },
        ],
      },
    })
    const trigger = wrapper.get('button')
    trigger.element.getBoundingClientRect = () => ({
      x: 640,
      y: 24,
      top: 24,
      right: 800,
      bottom: 56,
      left: 640,
      width: 160,
      height: 32,
      toJSON: () => ({}),
    })

    await trigger.trigger('click')
    await wrapper.vm.$nextTick()

    const content = document.body.querySelector('[role="listbox"]')
    expect(content).toBeTruthy()
    expect(content.style.width).toBe('var(--reka-combobox-trigger-width)')
    expect(content.style.minWidth).toBe('288px')
    expect(content.style.left).toBe('')
    expect(content.style.top).toBe('')
  })

  it('uses Reka dialog focus management and restores the opening control', async () => {
    const trigger = document.createElement('button')
    trigger.textContent = 'Open settings'
    document.body.append(trigger)
    trigger.focus()

    const wrapper = mount(DialogShell, {
      attachTo: document.body,
      props: { open: true, title: 'Settings' },
      slots: { default: '<button type="button">First setting</button>' },
    })
    await vi.waitFor(() => expect(document.activeElement?.textContent).toBe('First setting'))

    document.body.querySelector('[role="dialog"]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(1)
    await wrapper.setProps({ open: false })
    await vi.waitFor(() => expect(document.activeElement).toBe(trigger))
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
