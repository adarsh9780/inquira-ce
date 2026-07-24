import { localStateService } from '../services/localStateService.js'
import { useArtifactStore } from '../stores/artifactStore'
import { useConversationStore } from '../stores/conversationStore'
import { useExecutionStore } from '../stores/executionStore'
import { usePreferencesStore } from '../stores/preferencesStore'
import { useUiStore } from '../stores/uiStore'
import { useWorkspaceStore } from '../stores/workspaceStore'

const SNAPSHOT_VERSION = 2
let saveTimer: ReturnType<typeof setTimeout> | null = null

export function useSessionSnapshot() {
  const ui = useUiStore()
  const preferences = usePreferencesStore()
  const artifacts = useArtifactStore()
  const execution = useExecutionStore()
  const workspaces = useWorkspaceStore()
  const conversations = useConversationStore()

  function buildSnapshot() {
    return {
      version: SNAPSHOT_VERSION,
      ui: {
        activeTab: ui.activeTab,
        workspacePane: ui.workspacePane,
        dataPane: ui.dataPane,
        leftPaneWidth: ui.leftPaneWidth,
        terminalConsentGranted: ui.terminalConsentGranted,
        isTerminalOpen: ui.isTerminalOpen,
        terminalHeight: ui.terminalHeight,
        isSidebarCollapsed: ui.isSidebarCollapsed,
      },
      preferences: {
        llmProvider: preferences.llmProvider,
        selectedModel: preferences.selectedModel,
        selectedLiteModel: preferences.selectedLiteModel,
        selectedCodingModel: preferences.selectedCodingModel,
        slowRequestWarningSeconds: preferences.slowRequestWarningSeconds,
        allowLlmDataSamples: preferences.allowLlmDataSamples,
        uiTheme: preferences.uiTheme,
        uiFont: preferences.uiFont,
        uiCodeFont: preferences.uiCodeFont,
      },
      workspace: { activeWorkspaceId: workspaces.activeWorkspaceId },
      conversation: {
        activeConversationId: conversations.activeConversationId,
        questionHistory: conversations.questionHistory,
        conversationStateById: conversations.conversationStateById,
      },
      execution: {
        pythonFileContent: execution.pythonFileContent,
        userEditedCode: execution.userEditedCode,
        hasUserEditedCode: execution.hasUserEditedCode,
        codeEditorSource: execution.codeEditorSource,
        generatedCode: execution.generatedCode,
        terminalEntries: execution.terminalEntries,
        terminalEntriesTrimmedCount: execution.terminalEntriesTrimmedCount,
      },
      artifacts: {
        tablePageOffsets: artifacts.tablePageOffsets,
        selectedTableArtifactsByWorkspace: artifacts.selectedTableArtifactsByWorkspace,
        selectedFigureArtifactsByWorkspace: artifacts.selectedFigureArtifactsByWorkspace,
      },
    }
  }

  function applySnapshot(snapshotValue: unknown) {
    if (!snapshotValue || typeof snapshotValue !== 'object') return false
    const snapshot = snapshotValue as Record<string, any>
    const uiState = snapshot.ui || snapshot
    const preferenceState = snapshot.preferences || snapshot
    const workspaceState = snapshot.workspace || snapshot
    const conversationState = snapshot.conversation || snapshot
    const executionState = snapshot.execution || snapshot
    const artifactState = snapshot.artifacts || snapshot

    ui.activeTab = String(uiState.activeTab || 'workspace')
    ui.workspacePane = ['chat', 'code'].includes(String(uiState.workspacePane))
      ? String(uiState.workspacePane)
      : 'chat'
    ui.dataPane = ['table', 'figure', 'output'].includes(String(uiState.dataPane))
      ? String(uiState.dataPane)
      : 'table'
    ui.leftPaneWidth = Math.max(10, Math.min(90, Number(uiState.leftPaneWidth || 50)))
    ui.terminalConsentGranted = Boolean(uiState.terminalConsentGranted)
    ui.isTerminalOpen = Boolean(uiState.isTerminalOpen)
    ui.terminalHeight = Math.max(10, Math.min(90, Number(uiState.terminalHeight || 30)))
    ui.isSidebarCollapsed = Boolean(uiState.isSidebarCollapsed)

    preferences.llmProvider = String(preferenceState.llmProvider || preferences.llmProvider)
    preferences.selectedModel = String(preferenceState.selectedModel || preferences.selectedModel)
    preferences.selectedLiteModel = String(preferenceState.selectedLiteModel || preferences.selectedLiteModel)
    preferences.selectedCodingModel = String(preferenceState.selectedCodingModel || preferences.selectedCodingModel)
    preferences.slowRequestWarningSeconds = Math.max(10, Number(preferenceState.slowRequestWarningSeconds || 120))
    preferences.allowLlmDataSamples = Boolean(preferenceState.allowLlmDataSamples)
    preferences.setUiTheme(preferenceState.uiTheme, { persist: false })
    preferences.setUiFont(preferenceState.uiFont, { persist: false })
    preferences.setUiCodeFont(preferenceState.uiCodeFont, { persist: false })

    workspaces.setActiveWorkspaceId(workspaceState.activeWorkspaceId)
    conversations.activeConversationId = String(conversationState.activeConversationId || '')
    conversations.questionHistory = Array.isArray(conversationState.questionHistory)
      ? conversationState.questionHistory.slice(0, 30)
      : []
    conversations.conversationStateById = conversationState.conversationStateById || {}

    execution.pythonFileContent = String(executionState.pythonFileContent || '')
    execution.userEditedCode = String(executionState.userEditedCode || '')
    execution.hasUserEditedCode = Boolean(executionState.hasUserEditedCode)
    execution.codeEditorSource = executionState.codeEditorSource === 'user' ? 'user' : 'agent'
    execution.generatedCode = String(executionState.generatedCode || '')
    execution.terminalEntries = Array.isArray(executionState.terminalEntries)
      ? executionState.terminalEntries.slice(-50)
      : []
    execution.terminalEntriesTrimmedCount = Math.max(0, Number(executionState.terminalEntriesTrimmedCount || 0))

    artifacts.tablePageOffsets = artifactState.tablePageOffsets || {}
    artifacts.selectedTableArtifactsByWorkspace = artifactState.selectedTableArtifactsByWorkspace || {}
    artifacts.selectedFigureArtifactsByWorkspace = artifactState.selectedFigureArtifactsByWorkspace || {}
    return true
  }

  async function load(scope = 'default') {
    const snapshot = await localStateService.loadSnapshot(scope)
    return applySnapshot(snapshot)
  }

  async function flush(scope = 'default') {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    return localStateService.saveSnapshot(buildSnapshot(), scope)
  }

  function scheduleSave(scope = 'default') {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => void flush(scope), 150)
  }

  function configurePersistence(scope = 'default') {
    const persist = () => scheduleSave(scope)
    ui.configurePersistence(persist)
    preferences.configurePersistence(persist)
    artifacts.configurePersistence(persist)
  }

  function reset() {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = null
    ui.reset()
    preferences.reset()
    artifacts.reset()
    execution.reset()
    workspaces.reset()
    conversations.reset()
  }

  return { buildSnapshot, applySnapshot, load, flush, scheduleSave, configurePersistence, reset }
}
