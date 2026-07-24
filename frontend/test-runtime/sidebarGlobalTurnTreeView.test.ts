import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
vi.mock('../src/composables/useToast', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import SidebarGlobalTurnTree from '../src/components/layout/sidebar/SidebarGlobalTurnTree.vue'
import { useConversationStore } from '../src/stores/conversationStore'
import { useWorkspaceStore } from '../src/stores/workspaceStore'

describe('SidebarGlobalTurnTree graph view', () => {
  beforeEach(() => {
    const values = new Map()
    vi.stubGlobal('localStorage', {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
      clear: () => values.clear(),
    })
  })

  it('renders only the graph and opens the conversation tree rules', async () => {
    const setItem = vi.fn()
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem,
      clear: vi.fn(),
    })
    const pinia = createPinia()
    const workspaceStore = useWorkspaceStore(pinia)
    const conversationStore = useConversationStore(pinia)
    workspaceStore.activeWorkspaceId = 'workspace-1'
    conversationStore.workspaceTurnTree = { conversations: [] }
    conversationStore.loadWorkspaceTurnTree = vi.fn()

    const wrapper = mount(SidebarGlobalTurnTree, {
      global: {
        plugins: [pinia],
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
