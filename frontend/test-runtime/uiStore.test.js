import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import {
  normalizeDataPane,
  normalizeSettingsTab,
  normalizeWorkspacePane,
  useUiStore,
} from '../src/stores/uiStore'

describe('uiStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('normalizes pane and settings routes', () => {
    expect(normalizeWorkspacePane('CODE')).toBe('code')
    expect(normalizeWorkspacePane('unknown')).toBe('chat')
    expect(normalizeDataPane('figure')).toBe('figure')
    expect(normalizeDataPane('unknown')).toBe('table')
    expect(normalizeSettingsTab('llm')).toBe('connections')
    expect(normalizeSettingsTab('theme')).toBe('appearance')
  })

  it('keeps legacy tab routing in the workspace shell', () => {
    const store = useUiStore()

    store.setActiveTab('code')
    expect(store.activeTab).toBe('workspace')
    expect(store.workspacePane).toBe('code')

    store.setActiveTab('figure')
    expect(store.activeTab).toBe('workspace')
    expect(store.dataPane).toBe('figure')

    store.setActiveTab('terminal')
    expect(store.activeTab).toBe('workspace')
    expect(store.isTerminalOpen).toBe(true)
  })

  it('owns overlay, focus, and settings state independently', () => {
    const store = useUiStore()

    store.setSidebarCollapsed(true)
    store.openCommandPalette()
    store.setEditorPosition(12, 4)
    store.setEditorFocused(true)
    store.openSettings('workspace-ai')

    expect(store.isSidebarCollapsed).toBe(true)
    expect(store.isCommandPaletteOpen).toBe(true)
    expect(store.editorLine).toBe(12)
    expect(store.editorCol).toBe(4)
    expect(store.isEditorFocused).toBe(true)
    expect(store.isSettingsOpen).toBe(true)
    expect(store.settingsInitialTab).toBe('workspace-ai')
  })

  it('rejects unsafe pane dimensions', () => {
    const store = useUiStore()

    store.setLeftPaneWidth(5)
    store.setTerminalHeight(95)
    store.setChatOverlayWidth(0.95)

    expect(store.leftPaneWidth).toBe(50)
    expect(store.terminalHeight).toBe(30)
    expect(store.chatOverlayWidth).toBe(0.25)
  })
})
