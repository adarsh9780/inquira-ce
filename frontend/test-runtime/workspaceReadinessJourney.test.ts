import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WorkspaceReadinessJourney from '../src/components/chat/WorkspaceReadinessJourney.vue'

describe('WorkspaceReadinessJourney', () => {
  it.each([
    ['no_workspace', 'Create a workspace', 'Create workspace'],
    ['no_data', 'Connect your data', 'Add data'],
    ['model_connection_required', 'Connect an AI provider', 'Connect provider'],
    ['workspace_configuration_required', 'Review workspace AI', 'Review AI settings'],
  ])('presents one clear next action for %s', async (state, title, actionLabel) => {
    const wrapper = mount(WorkspaceReadinessJourney, { props: { state } })

    expect(wrapper.get('h2').text()).toBe(title)
    expect(wrapper.get('[data-primary-action]').text()).toContain(actionLabel)
    await wrapper.get('[data-primary-action]').trigger('click')
    expect(wrapper.emitted('primary-action')).toHaveLength(1)
  })
})
