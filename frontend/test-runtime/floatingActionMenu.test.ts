import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import FloatingActionMenu from '../src/components/ui/FloatingActionMenu.vue'

describe('FloatingActionMenu', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders headers, dividers, normal actions, and destructive disabled actions', async () => {
    const wrapper = mount(FloatingActionMenu, {
      attachTo: document.body,
      props: {
        isOpen: true,
        position: { x: 20, y: 30 },
        markerAttr: 'data-test-action-menu',
        header: '23 Jun 2026, 9:57 AM',
        items: [
          { id: 'rename', label: 'Rename' },
          { id: 'delete', label: 'Delete', destructive: true, dividerBefore: true, disabled: true },
        ],
      },
    })

    await wrapper.vm.$nextTick()
    const menu = document.body.querySelector('[data-test-action-menu]')
    expect(menu).toBeTruthy()
    expect(menu.textContent).toContain('23 Jun 2026, 9:57 AM')
    expect(menu.querySelectorAll('[data-floating-action-menu-divider]')).toHaveLength(1)
    expect(menu.querySelector('[data-action-id="delete"]').className).toContain('text-[var(--color-danger)]')
    expect(menu.querySelector('[data-action-id="delete"]').disabled).toBe(true)
  })

  it('emits select and close for actions, Escape, and outside pointerdown', async () => {
    const wrapper = mount(FloatingActionMenu, {
      attachTo: document.body,
      props: {
        isOpen: true,
        position: { x: 20, y: 30 },
        items: [{ id: 'rename', label: 'Rename' }],
      },
    })

    await wrapper.vm.$nextTick()
    document.body.querySelector('[data-action-id="rename"]').click()
    expect(wrapper.emitted('select')?.[0]).toEqual([
      'rename',
      {
        id: 'rename',
        label: 'Rename',
        destructive: false,
        dividerBefore: false,
        disabled: false,
        closeOnSelect: true,
      },
    ])
    expect(wrapper.emitted('close')).toHaveLength(1)

    await wrapper.setProps({ isOpen: true })
    await wrapper.vm.$nextTick()
    document.body.querySelector('[data-floating-action-menu]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(2)

    await wrapper.setProps({ isOpen: true })
    await wrapper.vm.$nextTick()
    document.body.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(3)
  })

  it('clamps menu position inside the viewport', async () => {
    const wrapper = mount(FloatingActionMenu, {
      attachTo: document.body,
      props: {
        isOpen: true,
        position: { x: 5000, y: 5000 },
        width: 180,
        height: 120,
        items: [{ id: 'rename', label: 'Rename' }],
      },
    })

    await wrapper.vm.$nextTick()
    const menu = document.body.querySelector('[data-floating-action-menu]')
    const left = Number.parseFloat(menu.style.left)
    const top = Number.parseFloat(menu.style.top)
    expect(left).toBeLessThanOrEqual(window.innerWidth - 180 - 8)
    expect(top).toBeLessThanOrEqual(window.innerHeight - 120 - 8)
  })
})
