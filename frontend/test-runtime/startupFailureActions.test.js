import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StartupFailureActions from '../src/components/startup/StartupFailureActions.vue'

describe('StartupFailureActions', () => {
  it('exposes accessible recovery actions and emits each operation', async () => {
    const wrapper = mount(StartupFailureActions, {
      props: { message: 'Diagnostics copied.' },
    })

    const group = wrapper.get('[aria-label="Startup recovery actions"]')
    const buttons = group.findAll('button')
    expect(buttons.map((button) => button.text())).toEqual([
      'Restart app',
      'Open logs',
      'Copy diagnostics',
    ])

    await buttons[0].trigger('click')
    await buttons[1].trigger('click')
    await buttons[2].trigger('click')

    expect(wrapper.emitted('restart')).toHaveLength(1)
    expect(wrapper.emitted('open-logs')).toHaveLength(1)
    expect(wrapper.emitted('copy-diagnostics')).toHaveLength(1)
    expect(wrapper.get('[aria-live="polite"]').text()).toBe('Diagnostics copied.')
  })
})
