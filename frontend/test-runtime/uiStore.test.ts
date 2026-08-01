import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUiStore } from '../src/stores/uiStore'

describe('uiStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('normalizes pane navigation without leaking retired routes', () => {
    const store = useUiStore()

    store.setActiveTab('code')
    expect(store.activeTab).toBe('workspace')
    expect(store.workspacePane).toBe('code')

    store.setActiveTab('ctree')
    expect(store.activeTab).toBe('workspace')
    expect(store.workspacePane).toBe('chat')

    store.setDataPane('unknown')
    expect(store.dataPane).toBe('table')
  })

  it('routes connection requests to Workspace Data without leaving Settings open', () => {
    const store = useUiStore()

    store.openSettings('workspace-ai')
    expect(store.isSettingsOpen).toBe(true)
    expect(store.settingsInitialTab).toBe('workspace-ai')

    store.requestConnectionFlow()
    expect(store.activeTab).toBe('schema-editor')
    expect(store.isSettingsOpen).toBe(false)
    expect(store.settingsInitialTab).toBe('workspace-ai')
    expect(store.connectionFlowRequestId).toBe(1)

    store.openConversationSwitcher()
    expect(store.isConversationSwitcherOpen).toBe(true)
    store.toggleConversationSwitcher()
    expect(store.isConversationSwitcherOpen).toBe(false)
  })

  it('bounds persisted pane sizes', () => {
    const store = useUiStore()

    store.setLeftPaneWidth(72)
    store.setTerminalHeight(44)
    expect(store.leftPaneWidth).toBe(72)
    expect(store.terminalHeight).toBe(44)

    store.setLeftPaneWidth(4)
    store.setTerminalHeight(95)
    expect(store.leftPaneWidth).toBe(72)
    expect(store.terminalHeight).toBe(44)
  })
})
