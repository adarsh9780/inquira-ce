import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const store = {
  activeWorkspaceId: 'workspace-1',
  workspaceTurnTree: { conversations: [] },
  activeTurnId: '',
  activeTurnRelations: null,
  loadWorkspaceTurnTree: vi.fn(),
}

vi.mock('../src/stores/appStore', () => ({ useAppStore: () => store }))
vi.mock('../src/composables/useToast', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import SidebarGlobalTurnTree from '../src/components/layout/sidebar/SidebarGlobalTurnTree.vue'

describe('SidebarGlobalTurnTree graph view', () => {
  beforeEach(() => {
    const values = new Map()
    vi.stubGlobal('localStorage', {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
      clear: () => values.clear(),
    })
    store.loadWorkspaceTurnTree.mockClear()
  })

  it('renders only the graph and opens the conversation tree rules', async () => {
    const setItem = vi.fn()
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem,
      clear: vi.fn(),
    })
    const wrapper = mount(SidebarGlobalTurnTree, {
      global: {
        stubs: {
          TurnTreeGraphView: { template: '<div data-view="graph"></div>' },
          ConversationTreeRulesModal: {
            props: ['isOpen'],
            template: '<div v-if="isOpen" data-rules-modal></div>',
          },
          ConfirmationModal: true,
        },
      },
    })

    expect(wrapper.get('[data-view="graph"]').exists()).toBe(true)
    expect(wrapper.find('[data-view="list"]').exists()).toBe(false)
    expect(wrapper.find('[data-rules-modal]').exists()).toBe(false)
    await wrapper.get('button[aria-label="Open conversation tree rules"]').trigger('click')
    expect(wrapper.get('[data-rules-modal]').exists()).toBe(true)
    expect(setItem).not.toHaveBeenCalled()
  })
})
