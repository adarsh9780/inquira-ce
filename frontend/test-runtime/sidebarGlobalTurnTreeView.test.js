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

describe('SidebarGlobalTurnTree view switcher', () => {
  beforeEach(() => {
    const values = new Map()
    vi.stubGlobal('localStorage', {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
      clear: () => values.clear(),
    })
    store.loadWorkspaceTurnTree.mockClear()
  })

  it('defaults to list, switches to graph, and persists the selection', async () => {
    const wrapper = mount(SidebarGlobalTurnTree, {
      global: {
        stubs: {
          TurnTreeView: { template: '<div data-view="list"></div>' },
          TurnTreeGraphView: { template: '<div data-view="graph"></div>' },
          ConfirmationModal: true,
        },
      },
    })

    expect(wrapper.get('[data-view="list"]').exists()).toBe(true)
    await wrapper.get('button[aria-pressed="false"]').trigger('click')
    expect(wrapper.get('[data-view="graph"]').exists()).toBe(true)
    expect(localStorage.getItem('inquira.conversation-tree.view')).toBe('graph')

    wrapper.unmount()
    const restored = mount(SidebarGlobalTurnTree, {
      global: {
        stubs: {
          TurnTreeView: { template: '<div data-view="list"></div>' },
          TurnTreeGraphView: { template: '<div data-view="graph"></div>' },
          ConfirmationModal: true,
        },
      },
    })
    expect(restored.get('[data-view="graph"]').exists()).toBe(true)
  })
})
