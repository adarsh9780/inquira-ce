import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const store = {
  activeTab: 'workspace',
  leftPaneWidth: 48,
  terminalHeight: 30,
  isTerminalOpen: true,
  setLeftPaneWidth: vi.fn(),
  setTerminalHeight: vi.fn(),
  toggleTerminal: vi.fn(),
}

vi.mock('../src/stores/uiStore', () => ({ useUiStore: () => store }))

import RightPanel from '../src/components/layout/RightPanel.vue'

describe('RightPanel resizers', () => {
  beforeEach(() => {
    store.setLeftPaneWidth.mockClear()
    store.setTerminalHeight.mockClear()
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      disconnect() {}
    })
  })

  it('exposes separator state and supports bounded keyboard resizing on both axes', async () => {
    const wrapper = mount(RightPanel, {
      global: {
        stubs: {
          WorkspaceContextBar: true,
          WorkspaceLeftPane: true,
          WorkspaceRightPane: true,
          SidebarGlobalTurnTree: true,
          TerminalTab: true,
          SchemaEditorTab: true,
          CommandLineIcon: true,
          XMarkIcon: true,
        },
      },
    })

    const horizontal = wrapper.get('[aria-label="Resize work and data panes"]')
    expect(horizontal.attributes('role')).toBe('separator')
    expect(horizontal.attributes('aria-valuenow')).toBe('48')
    await horizontal.trigger('keydown', { key: 'ArrowRight' })
    expect(store.setLeftPaneWidth).toHaveBeenCalledWith(50)
    await horizontal.trigger('keydown', { key: 'Home' })
    expect(store.setLeftPaneWidth).toHaveBeenCalledWith(20)

    const vertical = wrapper.get('[aria-label="Resize workspace and terminal panes"]')
    expect(vertical.attributes('aria-valuenow')).toBe('30')
    await vertical.trigger('keydown', { key: 'ArrowUp' })
    expect(store.setTerminalHeight).toHaveBeenCalledWith(32)
    await vertical.trigger('keydown', { key: 'End' })
    expect(store.setTerminalHeight).toHaveBeenCalledWith(80)
  })
})
