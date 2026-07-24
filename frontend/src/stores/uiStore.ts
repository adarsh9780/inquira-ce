import { defineStore } from 'pinia'
import { ref } from 'vue'

export type WorkspacePane = 'code' | 'chat'
export type DataPane = 'table' | 'figure' | 'output'
export type SettingsTab =
  | 'setup'
  | 'connections'
  | 'workspace-ai'
  | 'workspace-data'
  | 'workspace-general'
  | 'account'
  | 'appearance'
  | 'terms'

const WORKSPACE_PANES = new Set<WorkspacePane>(['code', 'chat'])
const DATA_PANES = new Set<DataPane>(['table', 'figure', 'output'])

export function normalizeWorkspacePane(pane: unknown): WorkspacePane {
  const normalized = String(pane || '').trim().toLowerCase() as WorkspacePane
  return WORKSPACE_PANES.has(normalized) ? normalized : 'chat'
}

export function normalizeDataPane(pane: unknown): DataPane {
  const normalized = String(pane || '').trim().toLowerCase() as DataPane
  return DATA_PANES.has(normalized) ? normalized : 'table'
}

export function normalizeSettingsTab(tab: unknown): SettingsTab {
  const normalized = String(tab || '').trim().toLowerCase()
  if (normalized === 'setup' || normalized === 'readiness') return 'setup'
  if (normalized === 'api' || normalized === 'llm' || normalized === 'connections') return 'connections'
  if (normalized === 'models' || normalized === 'workspace-ai') return 'workspace-ai'
  if (normalized === 'data' || normalized === 'workspace-data') return 'workspace-data'
  if (normalized === 'workspace' || normalized === 'workspace-general') return 'workspace-general'
  if (normalized === 'account') return 'account'
  if (normalized === 'appearance' || normalized === 'theme') return 'appearance'
  if (normalized === 'terms' || normalized === 'legal') return 'terms'
  return 'setup'
}

export const useUiStore = defineStore('ui', () => {
  const activeTab = ref('workspace')
  const workspacePane = ref<WorkspacePane>('chat')
  const dataPane = ref<DataPane>('table')
  const leftPaneWidth = ref(50)
  const isTerminalOpen = ref(false)
  const terminalHeight = ref(30)
  const isChatOverlayOpen = ref(true)
  const chatOverlayWidth = ref(0.25)
  const isSidebarCollapsed = ref(false)
  const hideShortcutsModal = ref(false)
  const isKeyboardShortcutsOpen = ref(false)
  const isCommandPaletteOpen = ref(false)
  const editorLine = ref(1)
  const editorCol = ref(1)
  const isEditorFocused = ref(false)
  const isSettingsOpen = ref(false)
  const settingsInitialTab = ref<SettingsTab>('setup')
  const isLoading = ref(false)

  function setActiveTab(tab: unknown) {
    const normalized = String(tab || '').trim().toLowerCase()
    if (normalized === 'code' || normalized === 'chat' || normalized === 'ctree') {
      activeTab.value = 'workspace'
      workspacePane.value = normalized === 'code' ? 'code' : 'chat'
      return
    }
    if (DATA_PANES.has(normalized as DataPane)) {
      activeTab.value = 'workspace'
      dataPane.value = normalized as DataPane
      return
    }
    if (normalized === 'terminal') {
      activeTab.value = 'workspace'
      isTerminalOpen.value = true
      return
    }
    activeTab.value = normalized === 'preview' ? 'workspace' : (normalized || 'workspace')
  }

  function setWorkspacePane(pane: unknown) {
    workspacePane.value = normalizeWorkspacePane(pane)
    activeTab.value = 'workspace'
  }

  function setDataPane(pane: unknown) {
    dataPane.value = normalizeDataPane(pane)
    activeTab.value = 'workspace'
  }

  function setLeftPaneWidth(widthPct: number) {
    if (widthPct >= 10 && widthPct <= 90) leftPaneWidth.value = widthPct
  }

  function setTerminalHeight(heightPct: number) {
    if (heightPct >= 10 && heightPct <= 90) terminalHeight.value = heightPct
  }

  function toggleTerminal() {
    isTerminalOpen.value = !isTerminalOpen.value
    if (isTerminalOpen.value && ['schema-editor', 'conversation-tree'].includes(activeTab.value)) {
      activeTab.value = 'workspace'
    }
  }

  function toggleChatOverlay() {
    isChatOverlayOpen.value = !isChatOverlayOpen.value
  }

  function setChatOverlayOpen(open: boolean) {
    isChatOverlayOpen.value = Boolean(open)
  }

  function setChatOverlayWidth(widthFraction: number) {
    if (widthFraction > 0.1 && widthFraction < 0.9) chatOverlayWidth.value = widthFraction
  }

  function setSidebarCollapsed(collapsed: boolean) {
    isSidebarCollapsed.value = Boolean(collapsed)
  }

  function setHideShortcutsModal(hide: boolean) {
    hideShortcutsModal.value = Boolean(hide)
  }

  function openKeyboardShortcuts() {
    isKeyboardShortcutsOpen.value = true
  }

  function closeKeyboardShortcuts() {
    isKeyboardShortcutsOpen.value = false
  }

  function openCommandPalette() {
    isCommandPaletteOpen.value = true
  }

  function closeCommandPalette() {
    isCommandPaletteOpen.value = false
  }

  function toggleCommandPalette() {
    isCommandPaletteOpen.value = !isCommandPaletteOpen.value
  }

  function setEditorPosition(line: number, col: number) {
    editorLine.value = line
    editorCol.value = col
  }

  function setEditorFocused(focused: boolean) {
    isEditorFocused.value = Boolean(focused)
  }

  function openSettings(tab: unknown = 'setup') {
    settingsInitialTab.value = normalizeSettingsTab(tab)
    isSettingsOpen.value = true
  }

  function closeSettings() {
    isSettingsOpen.value = false
  }

  return {
    activeTab,
    workspacePane,
    dataPane,
    leftPaneWidth,
    isTerminalOpen,
    terminalHeight,
    isChatOverlayOpen,
    chatOverlayWidth,
    isSidebarCollapsed,
    hideShortcutsModal,
    isKeyboardShortcutsOpen,
    isCommandPaletteOpen,
    editorLine,
    editorCol,
    isEditorFocused,
    isSettingsOpen,
    settingsInitialTab,
    isLoading,
    setActiveTab,
    setWorkspacePane,
    setDataPane,
    setLeftPaneWidth,
    setTerminalHeight,
    toggleTerminal,
    toggleChatOverlay,
    setChatOverlayOpen,
    setChatOverlayWidth,
    setSidebarCollapsed,
    setHideShortcutsModal,
    openKeyboardShortcuts,
    closeKeyboardShortcuts,
    openCommandPalette,
    closeCommandPalette,
    toggleCommandPalette,
    setEditorPosition,
    setEditorFocused,
    openSettings,
    closeSettings,
  }
})
