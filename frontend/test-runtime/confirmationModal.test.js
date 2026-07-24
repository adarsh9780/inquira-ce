import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import ConfirmationModal from '../src/components/modals/ConfirmationModal.vue'

const mounted = []

async function renderModal(props = {}) {
  const wrapper = mount(ConfirmationModal, {
    attachTo: document.body,
    props: {
      isOpen: true,
      title: 'Delete workspace',
      message: 'This action cannot be undone.',
      ...props,
    },
  })
  mounted.push(wrapper)
  await nextTick()
  await nextTick()
  return wrapper
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount()
  document.body.innerHTML = ''
})

describe('ConfirmationModal', () => {
  it('renders an accessible alert dialog in a portal', async () => {
    await renderModal()

    const dialog = document.querySelector('[role="alertdialog"]')
    expect(dialog).not.toBeNull()
    expect(dialog?.textContent).toContain('Delete workspace')
    expect(dialog?.textContent).toContain('This action cannot be undone.')
  })

  it('emits confirm from the destructive action', async () => {
    const wrapper = await renderModal()
    const confirm = [...document.querySelectorAll('button')]
      .find((button) => button.textContent?.trim() === 'Confirm')

    confirm?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('emits close from the cancel action', async () => {
    const wrapper = await renderModal()
    const cancel = [...document.querySelectorAll('button')]
      .find((button) => button.textContent?.trim() === 'Cancel')

    cancel?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
