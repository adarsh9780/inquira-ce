import { defineStore } from 'pinia'
import { ref } from 'vue'

const WORKSPACE_PANES = new Set(['code', 'chat'])
const DATA_PANES = new Set(['table', 'figure', 'output'])

function normalizeWorkspacePane(pane: unknown) {
  const normalized = String(pane || '').trim().toLowerCase()
  return WORKSPACE_PANES.has(normalized) ? normalized : 'chat'
}

function normalizeDataPane(pane: unknown) {
  const normalized = String(pane || '').trim().toLowerCase()
  return DATA_PANES.has(normalized) ? normalized : 'table'
}

export const useUiStore = defineStore('ui', () => {
  let persistChange: (() => void) | null = null
  const activeTab = ref('workspace')
  const workspacePane = ref('chat')
  const dataPane = ref('table')
  const leftPaneWidth = ref(50)
  const terminalConsentGranted = ref(false)
  const isTerminalOpen = ref(false)
  const terminalHeight = ref(30)
  const terminalCwd = ref('')
  const isSidebarCollapsed = ref(false)
  const isKeyboardShortcutsOpen = ref(false)
  const isConversationSwitcherOpen = ref(false)
  const connectionFlowRequestId = ref(0)
  const editorLine = ref(1)
  const editorCol = ref(1)
  const isEditorFocused = ref(false)
  const isLoading = ref(false)
  const isSettingsOpen = ref(false)
  const settingsInitialTab = ref('setup')

  function configurePersistence(handler: (() => void) | null) {
    persistChange = handler
  }

  function persist() {
    persistChange?.()
  }

  function openSettings(tab = 'setup') {
    const normalized = String(tab || '').trim().toLowerCase()
    if (normalized === 'setup' || normalized === 'readiness') settingsInitialTab.value = 'setup'
    else if (['api', 'llm', 'connections'].includes(normalized)) settingsInitialTab.value = 'connections'
    else if (normalized === 'models' || normalized === 'workspace-ai') settingsInitialTab.value = 'workspace-ai'
    else if (normalized === 'data' || normalized === 'workspace-data') settingsInitialTab.value = 'workspace-data'
    else if (normalized === 'workspace' || normalized === 'workspace-general') settingsInitialTab.value = 'workspace-general'
    else if (normalized === 'account') settingsInitialTab.value = 'account'
    else if (normalized === 'appearance' || normalized === 'theme') settingsInitialTab.value = 'appearance'
    else if (normalized === 'terms' || normalized === 'legal') settingsInitialTab.value = 'terms'
    else settingsInitialTab.value = 'setup'
    isSettingsOpen.value = true
  }

  function setActiveTab(tab: unknown) {
    const normalized = String(tab || '').trim().toLowerCase()
    if (normalized === 'code' || normalized === 'chat' || normalized === 'ctree') {
      activeTab.value = 'workspace'
      workspacePane.value = normalized === 'code' ? 'code' : 'chat'
    } else if (DATA_PANES.has(normalized)) {
      activeTab.value = 'workspace'
      dataPane.value = normalized
    } else if (normalized === 'terminal') {
      activeTab.value = 'workspace'
      isTerminalOpen.value = true
    } else if (normalized === 'preview') {
      activeTab.value = 'workspace'
    } else {
      activeTab.value = normalized || 'workspace'
    }
    persist()
  }

  function setWorkspacePane(pane: unknown) {
    workspacePane.value = normalizeWorkspacePane(pane)
    activeTab.value = 'workspace'
    persist()
  }

  function setDataPane(pane: unknown) {
    dataPane.value = normalizeDataPane(pane)
    activeTab.value = 'workspace'
    persist()
  }

  function setLeftPaneWidth(widthPct: number) {
    if (widthPct >= 10 && widthPct <= 90) {
      leftPaneWidth.value = widthPct
      persist()
    }
  }

  function setTerminalHeight(heightPct: number) {
    if (heightPct >= 10 && heightPct <= 90) {
      terminalHeight.value = heightPct
      persist()
    }
  }

  function toggleTerminal() {
    isTerminalOpen.value = !isTerminalOpen.value
    if (isTerminalOpen.value && ['schema-editor', 'conversation-tree'].includes(activeTab.value)) {
      activeTab.value = 'workspace'
    }
    persist()
  }

  function setTerminalConsentGranted(granted: unknown) {
    terminalConsentGranted.value = Boolean(granted)
    persist()
  }

  function setTerminalCwd(cwd: unknown) {
    terminalCwd.value = String(cwd || '')
  }

  function setSidebarCollapsed(collapsed: unknown) {
    isSidebarCollapsed.value = Boolean(collapsed)
    persist()
  }

  function openKeyboardShortcuts() {
    isKeyboardShortcutsOpen.value = true
  }

  function closeKeyboardShortcuts() {
    isKeyboardShortcutsOpen.value = false
  }

  function setConversationSwitcherOpen(open: unknown) {
    isConversationSwitcherOpen.value = Boolean(open)
  }

  function openConversationSwitcher() {
    setConversationSwitcherOpen(true)
  }

  function closeConversationSwitcher() {
    setConversationSwitcherOpen(false)
  }

  function toggleConversationSwitcher() {
    setConversationSwitcherOpen(!isConversationSwitcherOpen.value)
  }

  function requestConnectionFlow() {
    settingsInitialTab.value = 'workspace-data'
    connectionFlowRequestId.value += 1
    isSettingsOpen.value = true
  }

  function setEditorPosition(line: number, col: number) {
    editorLine.value = line
    editorCol.value = col
  }

  function setEditorFocused(focused: unknown) {
    isEditorFocused.value = Boolean(focused)
  }

  function setLoading(loading: unknown) {
    isLoading.value = Boolean(loading)
  }

  function reset() {
    activeTab.value = 'workspace'
    workspacePane.value = 'chat'
    dataPane.value = 'table'
    leftPaneWidth.value = 50
    terminalConsentGranted.value = false
    isTerminalOpen.value = false
    terminalHeight.value = 30
    terminalCwd.value = ''
    isSidebarCollapsed.value = false
    isKeyboardShortcutsOpen.value = false
    isConversationSwitcherOpen.value = false
    connectionFlowRequestId.value = 0
    editorLine.value = 1
    editorCol.value = 1
    isEditorFocused.value = false
    isLoading.value = false
    isSettingsOpen.value = false
    settingsInitialTab.value = 'setup'
  }

  return {
    activeTab,
    workspacePane,
    dataPane,
    leftPaneWidth,
    terminalConsentGranted,
    isTerminalOpen,
    terminalHeight,
    terminalCwd,
    isSidebarCollapsed,
    isKeyboardShortcutsOpen,
    isConversationSwitcherOpen,
    connectionFlowRequestId,
    editorLine,
    editorCol,
    isEditorFocused,
    isLoading,
    isSettingsOpen,
    settingsInitialTab,
    configurePersistence,
    openSettings,
    setActiveTab,
    setWorkspacePane,
    setDataPane,
    setLeftPaneWidth,
    setTerminalHeight,
    toggleTerminal,
    setTerminalConsentGranted,
    setTerminalCwd,
    setSidebarCollapsed,
    openKeyboardShortcuts,
    closeKeyboardShortcuts,
    setConversationSwitcherOpen,
    openConversationSwitcher,
    closeConversationSwitcher,
    toggleConversationSwitcher,
    requestConnectionFlow,
    setEditorPosition,
    setEditorFocused,
    setLoading,
    reset,
  }
})
