import { defineStore, storeToRefs } from 'pinia'
import { ref, computed, watch, markRaw } from 'vue'
import { apiService } from '../services/apiService'
import { workspaceService } from '../services/workspaceService'
import { localStateService } from '../services/localStateService'
import { useAuthStore } from './authStore'
import { useUiStore } from './uiStore'
import { usePreferencesStore } from './preferencesStore'
import { useArtifactStore } from './artifactStore'
import { useExecutionStore } from './executionStore'
import { useWorkspaceStore } from './workspaceStore'
import { useConversationStore } from './conversationStore'
import { normalizePlotlyFigure } from '../utils/figurePayload'
import { DEFAULT_THEME_ID, THEME_OPTIONS, normalizeThemeId } from '../constants/themes'
import {
  APP_FONT_OPTIONS,
  CODE_FONT_OPTIONS,
  DEFAULT_APP_FONT_ID,
  DEFAULT_CODE_FONT_ID,
  normalizeAppFontId,
  normalizeCodeFontId,
} from '../constants/fonts'
import { mergeUsageTotals, normalizeUsage } from '../utils/usageFormat'

export const useAppStore = defineStore('app', () => {
  const authStore = useAuthStore()
  const uiStore = useUiStore()
  const preferencesStore = usePreferencesStore()
  const artifactStore = useArtifactStore()
  const executionStore = useExecutionStore()
  const workspaceStore = useWorkspaceStore()
  const conversationStore = useConversationStore()
  const {
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
    isCommandPaletteOpen,
    connectionFlowRequestId,
    editorLine,
    editorCol,
    isEditorFocused,
    isLoading,
    isSettingsOpen,
    settingsInitialTab,
  } = storeToRefs(uiStore)
  const {
    llmProvider,
    availableProviders,
    selectedModel,
    selectedLiteModel,
    selectedCodingModel,
    slowRequestWarningSeconds,
    availableModels,
    providerMainModels,
    providerLiteModels,
    providerModelSearchResults,
    providerModelSearchLoading,
    providerModelSearchQuery,
    providerModelCatalogs,
    providerRequiresApiKey,
    apiKeyPresenceByProvider,
    selectedProviderApiKeyPresent,
    apiKey,
    apiKeyConfigured,
    allowLlmDataSamples,
    uiTheme,
    availableThemes,
    uiFont,
    availableFonts,
    uiCodeFont,
    availableCodeFonts,
  } = storeToRefs(preferencesStore)
  const {
    activeTurnArtifactRefreshKey,
    resultData,
    plotlyFigure,
    dataframes,
    figures,
    scalars,
    promotedUserDataframes,
    promotedUserFigures,
    dataframeCount,
    tableRowCount,
    tableWindowStart,
    tableWindowEnd,
    tablePageOffsets,
    selectedTableArtifactsByWorkspace,
    selectedFigureArtifactsByWorkspace,
    dataPaneError,
    figureCount,
  } = storeToRefs(artifactStore)
  const {
    pythonFileContent,
    userEditedCode,
    hasUserEditedCode,
    codeEditorSource,
    generatedCode,
    conversationRuns,
    workspaceRuntimeStatusById,
    terminalOutput,
    terminalEntries,
    terminalEntriesTrimmedCount,
    runtimeError,
    isCodeRunning,
    backgroundOperations,
  } = storeToRefs(executionStore)
  const {
    columnCatalog,
    workspaces,
    activeWorkspaceSummary,
    workspaceAIConfig,
    activeWorkspaceId,
    schemaContext,
  } = storeToRefs(workspaceStore)
  const {
    chatHistory,
    questionHistory,
    currentQuestion,
    liveTokenUsage,
    activeConversationUsage,
    conversationUsageById,
    conversations,
    activeConversationId,
    conversationStateById,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnRelations,
    workspaceTurnTree,
    finalTurnId,
  } = storeToRefs(conversationStore)
  const DEFAULT_MODELS = [
    'google/gemini-3-flash-preview',
    'google/gemini-2.5-flash',
    'google/gemini-2.5-flash-lite',
    'openrouter/free'
  ]
  const DEFAULT_PROVIDER = 'openrouter'
  const DEFAULT_LITE_MODEL = 'google/gemini-2.5-flash-lite'
  const DEFAULT_PROVIDER_LIST = ['openrouter', 'openai', 'anthropic', 'ollama']
  const DEFAULT_SLOW_REQUEST_WARNING_SECONDS = 120

  // Analysis
  // UI State

  function openSettings(tab = 'setup') {
    uiStore.openSettings(tab)
  }

  function openDataConnectionFlow() {
    const activeId = String(activeWorkspaceId.value || '').trim()
    const workspaceExists = activeId && workspaces.value.some((workspace) => workspace.id === activeId)
    if (!workspaceExists) {
      openSettings('workspace-general')
      return
    }
    uiStore.requestConnectionFlow()
  }

  // Computed
  const hasWorkspace = computed(() => {
    const activeId = activeWorkspaceId.value.trim()
    if (!activeId) return false
    return workspaces.value.some((ws) => ws.id === activeId)
  })
  const canAnalyze = computed(() => {
    const hasProviderAccess = workspaceAIConfig.value?.readiness
      ? Boolean(workspaceAIConfig.value.readiness.credential_ready)
      : (providerRequiresApiKey.value ? selectedProviderApiKeyPresent.value : true)
    if (!hasProviderAccess) return false
    return workspaceReadiness.value.ready
  })
  const workspaceReadiness = computed(() => {
    if (!hasWorkspace.value) return { state: 'no_workspace', ready: false }
    const aiReadiness = workspaceAIConfig.value?.readiness
    if (aiReadiness && !aiReadiness.credential_ready) return { state: 'model_connection_required', ready: false }
    if (aiReadiness && (!aiReadiness.model_ready || !aiReadiness.configuration_reviewed)) return { state: 'workspace_configuration_required', ready: false }
    const tableCount = Number(activeWorkspaceSummary.value?.table_count || 0)
    if (tableCount < 1) return { state: 'no_data', ready: false }
    return { state: 'ready', ready: true }
  })
  const activeWorkspaceRuntimeStatus = computed(() => getWorkspaceRuntimeStatus())
  const activeConversationIsLoading = computed(() => isConversationRunning(activeConversationId.value))
  const runningConversationCount = computed(() => (
    Object.values(conversationRuns.value || {})
      .filter((item) => String(item?.status || '') === 'running')
      .length
  ))
  const activeBackgroundOperations = computed(() => {
    const items = Array.isArray(backgroundOperations.value) ? backgroundOperations.value : []
    return items.filter((item) => ['queued', 'running', 'failed', 'complete'].includes(String(item?.status || '')))
  })
  const primaryBackgroundOperation = computed(() => {
    const items = activeBackgroundOperations.value
    const running = items.filter((item) => ['queued', 'running'].includes(String(item?.status || '')))
    const candidates = running.length ? running : items
    return candidates
      .slice()
      .sort((left, right) => {
        const priorityDelta = Number(right?.priority || 0) - Number(left?.priority || 0)
        if (priorityDelta !== 0) return priorityDelta
        return Number(right?.updatedAt || 0) - Number(left?.updatedAt || 0)
      })[0] || null
  })

  let preferenceSyncTimer = null
  let localStateSyncTimer = null
  let suppressPreferenceSync = false
  let providerModelSearchToken = 0
  const ensuredRuntimeWorkspaceIds = new Set()
  const LOCAL_SNAPSHOT_VERSION = 1
  const MAX_TERMINAL_ENTRIES = 50
  const MAX_TERMINAL_STREAM_CHARS = 200000
  const MAX_TERMINAL_TOTAL_CHARS = 2000000
  const MAX_QUESTION_HISTORY = 30
  function normalizeWorkspacePane(pane) {
    const normalized = String(pane || '').trim().toLowerCase()
    return ['code', 'chat'].includes(normalized) ? normalized : 'chat'
  }

  function cloneConversationValue(value) {
    if (Array.isArray(value)) return value.map((item) => cloneConversationValue(item))
    if (!value || typeof value !== 'object') return value
    return { ...value }
  }

  function normalizeConversationId(conversationId = activeConversationId.value) {
    return String(conversationId || '').trim()
  }

  function isActiveConversation(conversationId) {
    const id = normalizeConversationId(conversationId)
    return Boolean(id && id === normalizeConversationId(activeConversationId.value))
  }

  function getSelectedTableArtifactForActiveWorkspace() {
    const key = workspaceSelectionKey(activeWorkspaceId.value)
    return key ? String(selectedTableArtifactsByWorkspace.value?.[key] || '') : ''
  }

  function getSelectedFigureArtifactForActiveWorkspace() {
    const key = workspaceSelectionKey(activeWorkspaceId.value)
    return key ? String(selectedFigureArtifactsByWorkspace.value?.[key] || '') : ''
  }

  function buildConversationStateSnapshot(options = {}) {
    const existing = options?.existing && typeof options.existing === 'object' ? options.existing : {}
    return {
      ...existing,
      chatHistory: cloneConversationValue(chatHistory.value),
      currentQuestion: currentQuestion.value,
      activeTurnId: activeTurnId.value,
      activeTurn: cloneConversationValue(activeTurn.value),
      activeTurnCode: activeTurnCode.value,
      activeTurnRelations: cloneConversationValue(activeTurnRelations.value),
      finalTurnId: finalTurnId.value,
      liveTokenUsage: cloneConversationValue(liveTokenUsage.value),
      activeConversationUsage: cloneConversationValue(activeConversationUsage.value),
      generatedCode: generatedCode.value,
      pythonFileContent: pythonFileContent.value,
      userEditedCode: userEditedCode.value,
      hasUserEditedCode: hasUserEditedCode.value,
      codeEditorSource: codeEditorSource.value,
      resultData: cloneConversationValue(resultData.value),
      plotlyFigure: cloneConversationValue(plotlyFigure.value),
      dataframes: cloneConversationValue(dataframes.value),
      figures: cloneConversationValue(figures.value),
      scalars: cloneConversationValue(scalars.value),
      dataframeCount: dataframeCount.value,
      tableRowCount: tableRowCount.value,
      tableWindowStart: tableWindowStart.value,
      tableWindowEnd: tableWindowEnd.value,
      selectedTableArtifactId: getSelectedTableArtifactForActiveWorkspace(),
      selectedFigureArtifactId: getSelectedFigureArtifactForActiveWorkspace(),
      dataPane: dataPane.value,
      dataPaneError: dataPaneError.value,
      figureCount: figureCount.value,
      terminalOutput: terminalOutput.value,
      updatedAt: Date.now(),
    }
  }

  function setConversationState(conversationId, statePatch = {}) {
    const id = normalizeConversationId(conversationId)
    if (!id) return null
    const current = conversationStateById.value?.[id] || {}
    const next = {
      ...current,
      ...statePatch,
      updatedAt: Date.now(),
    }
    conversationStateById.value = {
      ...(conversationStateById.value || {}),
      [id]: next,
    }
    return next
  }

  function patchConversationState(conversationId, statePatch = {}) {
    const id = normalizeConversationId(conversationId)
    if (!id || !statePatch || typeof statePatch !== 'object') return null
    if (isActiveConversation(id)) {
      if (Object.prototype.hasOwnProperty.call(statePatch, 'chatHistory')) chatHistory.value = cloneConversationValue(statePatch.chatHistory || [])
      if (Object.prototype.hasOwnProperty.call(statePatch, 'currentQuestion')) currentQuestion.value = String(statePatch.currentQuestion || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'generatedCode')) generatedCode.value = String(statePatch.generatedCode || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'pythonFileContent')) pythonFileContent.value = String(statePatch.pythonFileContent || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'userEditedCode')) userEditedCode.value = String(statePatch.userEditedCode || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'hasUserEditedCode')) hasUserEditedCode.value = Boolean(statePatch.hasUserEditedCode)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'codeEditorSource')) codeEditorSource.value = statePatch.codeEditorSource === 'user' ? 'user' : 'agent'
      if (Object.prototype.hasOwnProperty.call(statePatch, 'resultData')) resultData.value = cloneConversationValue(statePatch.resultData || null)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'plotlyFigure')) plotlyFigure.value = cloneConversationValue(statePatch.plotlyFigure || null)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'dataframes')) dataframes.value = cloneConversationValue(statePatch.dataframes || [])
      if (Object.prototype.hasOwnProperty.call(statePatch, 'figures')) figures.value = cloneConversationValue(statePatch.figures || [])
      if (Object.prototype.hasOwnProperty.call(statePatch, 'scalars')) scalars.value = cloneConversationValue(statePatch.scalars || [])
      if (Object.prototype.hasOwnProperty.call(statePatch, 'dataframeCount')) dataframeCount.value = Number(statePatch.dataframeCount || 0)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'figureCount')) figureCount.value = Number(statePatch.figureCount || 0)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'terminalOutput')) terminalOutput.value = String(statePatch.terminalOutput || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'dataPane')) dataPane.value = ['table', 'figure', 'output'].includes(String(statePatch.dataPane || '')) ? statePatch.dataPane : dataPane.value
      if (Object.prototype.hasOwnProperty.call(statePatch, 'activeTurnId')) activeTurnId.value = String(statePatch.activeTurnId || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'activeTurn')) activeTurn.value = cloneConversationValue(statePatch.activeTurn || null)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'activeTurnCode')) activeTurnCode.value = String(statePatch.activeTurnCode || '')
      if (Object.prototype.hasOwnProperty.call(statePatch, 'activeTurnRelations')) activeTurnRelations.value = cloneConversationValue(statePatch.activeTurnRelations || null)
      if (Object.prototype.hasOwnProperty.call(statePatch, 'finalTurnId')) finalTurnId.value = String(statePatch.finalTurnId || '')
      return syncActiveConversationState({ conversationId: id })
    }
    return setConversationState(id, statePatch)
  }

  function getConversationState(conversationId, options = {}) {
    const id = normalizeConversationId(conversationId)
    if (!id) return null
    const existing = conversationStateById.value?.[id]
    if (existing || options?.create !== true) return existing || null
    return setConversationState(id, {
      chatHistory: [],
      currentQuestion: '',
      activeTurnId: '',
      activeTurn: null,
      activeTurnCode: '',
      activeTurnRelations: null,
      finalTurnId: '',
      liveTokenUsage: null,
      activeConversationUsage: null,
      generatedCode: '',
      pythonFileContent: '',
      userEditedCode: '',
      hasUserEditedCode: false,
      codeEditorSource: 'agent',
      resultData: null,
      plotlyFigure: null,
      dataframes: [],
      figures: [],
      scalars: [],
      dataframeCount: 0,
      tableRowCount: 0,
      tableWindowStart: 0,
      tableWindowEnd: 0,
      selectedTableArtifactId: '',
      selectedFigureArtifactId: '',
      dataPane: dataPane.value,
      dataPaneError: '',
      figureCount: 0,
      terminalOutput: '',
    })
  }

  function syncActiveConversationState(options = {}) {
    const id = normalizeConversationId(options?.conversationId || activeConversationId.value)
    if (!id || id !== normalizeConversationId(activeConversationId.value)) return null
    const existing = conversationStateById.value?.[id] || {}
    return setConversationState(id, buildConversationStateSnapshot({ existing }))
  }

  function applyConversationStateToActive(conversationId, state) {
    const id = normalizeConversationId(conversationId)
    if (!id) {
      clearConversationScopedState()
      return
    }
    const source = state && typeof state === 'object' ? state : getConversationState(id, { create: true })
    if (!source) {
      clearConversationScopedState()
      return
    }
    chatHistory.value = cloneConversationValue(source.chatHistory || [])
    currentQuestion.value = String(source.currentQuestion || '')
    activeTurnId.value = String(source.activeTurnId || '')
    activeTurn.value = cloneConversationValue(source.activeTurn || null)
    activeTurnCode.value = String(source.activeTurnCode || '')
    activeTurnRelations.value = cloneConversationValue(source.activeTurnRelations || null)
    finalTurnId.value = String(source.finalTurnId || '')
    liveTokenUsage.value = cloneConversationValue(source.liveTokenUsage || null)
    activeConversationUsage.value = cloneConversationValue(source.activeConversationUsage || null)
    generatedCode.value = String(source.generatedCode || '')
    pythonFileContent.value = String(source.pythonFileContent || '')
    userEditedCode.value = String(source.userEditedCode || '')
    hasUserEditedCode.value = Boolean(source.hasUserEditedCode)
    codeEditorSource.value = source.codeEditorSource === 'user' ? 'user' : 'agent'
    resultData.value = cloneConversationValue(source.resultData || null)
    plotlyFigure.value = cloneConversationValue(source.plotlyFigure || null)
    dataframes.value = cloneConversationValue(source.dataframes || [])
    figures.value = cloneConversationValue(source.figures || [])
    scalars.value = cloneConversationValue(source.scalars || [])
    dataframeCount.value = Number(source.dataframeCount || 0)
    tableRowCount.value = Number(source.tableRowCount || 0)
    tableWindowStart.value = Number(source.tableWindowStart || 0)
    tableWindowEnd.value = Number(source.tableWindowEnd || 0)
    dataPane.value = ['table', 'figure', 'output'].includes(String(source.dataPane || '')) ? source.dataPane : dataPane.value
    dataPaneError.value = String(source.dataPaneError || '')
    figureCount.value = Number(source.figureCount || 0)
    terminalOutput.value = String(source.terminalOutput || '')
    if (activeWorkspaceId.value) {
      setSelectedTableArtifact(activeWorkspaceId.value, source.selectedTableArtifactId || '')
      setSelectedFigureArtifact(activeWorkspaceId.value, source.selectedFigureArtifactId || '')
    }
  }

  function mutateConversationState(conversationId, mutator) {
    const id = normalizeConversationId(conversationId)
    if (!id || typeof mutator !== 'function') return null
    if (isActiveConversation(id)) {
      const result = mutator(null, true)
      syncActiveConversationState({ conversationId: id })
      return result
    }
    const current = getConversationState(id, { create: true })
    const draft = {
      ...current,
      chatHistory: Array.isArray(current.chatHistory) ? [...current.chatHistory] : [],
    }
    const result = mutator(draft, false)
    setConversationState(id, draft)
    return result
  }

  function normalizeSlowRequestWarningSeconds(rawValue) {
    const parsed = Number.parseInt(rawValue, 10)
    if (!Number.isFinite(parsed)) return DEFAULT_SLOW_REQUEST_WARNING_SECONDS
    return Math.min(600, Math.max(5, parsed))
  }

  function modelAllowedForProvider(provider, modelId) {
    const normalizedProvider = String(provider || '').trim().toLowerCase()
    const value = String(modelId || '').trim().toLowerCase()
    if (!value) return false
    if (normalizedProvider && normalizedProvider !== 'ollama' && value.includes(':cloud')) {
      return false
    }
    return true
  }

  function normalizeModelList(models, provider = '') {
    const raw = Array.isArray(models) ? models : []
    const seen = new Set()
    const cleaned = []
    for (const item of raw) {
      const value = String(item || '').trim()
      if (!value || seen.has(value)) continue
      if (provider && !modelAllowedForProvider(provider, value)) continue
      seen.add(value)
      cleaned.push(value)
    }
    return cleaned
  }

  function normalizeProviderName(provider) {
    const value = String(provider || '').trim().toLowerCase()
    return value || DEFAULT_PROVIDER
  }

  function normalizeSearchModelIds(models, provider = '') {
    const raw = Array.isArray(models) ? models : []
    const modelIds = raw
      .map((item) => {
        if (typeof item === 'string' || typeof item === 'number') return String(item || '').trim()
        if (!item || typeof item !== 'object') return ''
        return String(item.id || item.value || item.model || '').trim()
      })
      .filter(Boolean)
    return normalizeModelList(modelIds, provider)
  }

  function providerModelSearchCacheKey(provider, query) {
    return `${normalizeProviderName(provider)}::${String(query || '').trim().toLowerCase()}`
  }

  function clearProviderModelSearchState() {
    providerModelSearchResults.value = {}
    providerModelSearchLoading.value = false
    providerModelSearchQuery.value = ''
    providerModelSearchToken += 1
  }

  function mergeProviderModelOptions(provider, results = []) {
    const normalizedProvider = normalizeProviderName(provider)
    const selected = String(selectedModel.value || '').trim()
    const displayModels = normalizeModelList(providerMainModels.value, normalizedProvider)
    const searchModels = normalizeModelList(results, normalizedProvider)
    const merged = []
    if (selected && modelAllowedForProvider(normalizedProvider, selected)) {
      merged.push(selected)
    }
    merged.push(...displayModels)
    merged.push(...searchModels)
    availableModels.value = normalizeModelList(merged, normalizedProvider)
    return availableModels.value
  }

  function resolveSnapshotUserId(explicitUserId = null) {
    const candidate = String(explicitUserId ?? authStore.userId ?? '').trim()
    return candidate || ''
  }

  function buildLocalStateSnapshot() {
    return {
      version: LOCAL_SNAPSHOT_VERSION,
      updated_at: new Date().toISOString(),
      llm: {
        llm_provider: llmProvider.value || DEFAULT_PROVIDER,
        selected_model: selectedModel.value || '',
        selected_lite_model: selectedLiteModel.value || '',
        selected_coding_model: selectedModel.value || '',
        slow_request_warning_seconds: normalizeSlowRequestWarningSeconds(slowRequestWarningSeconds.value),
        allow_llm_data_samples: allowLlmDataSamples.value,
        provider_main_models: Array.isArray(providerMainModels.value) ? [...providerMainModels.value] : [],
        provider_lite_models: Array.isArray(providerLiteModels.value) ? [...providerLiteModels.value] : [],
      },
      ui: {
        ui_theme: uiTheme.value,
        ui_font: uiFont.value,
        ui_code_font: uiCodeFont.value,
        active_tab: activeTab.value || 'workspace',
        workspace_pane: workspacePane.value || 'chat',
        data_pane: dataPane.value || 'table',
        left_pane_width: Number(leftPaneWidth.value || 50),
        terminal_open: !!isTerminalOpen.value,
        terminal_consent_granted: !!terminalConsentGranted.value,
        terminal_height: Number(terminalHeight.value || 30),
        is_sidebar_collapsed: !!isSidebarCollapsed.value,
        table_row_count: Number(tableRowCount.value || 0),
        table_window_start: Number(tableWindowStart.value || 0),
        table_window_end: Number(tableWindowEnd.value || 0),
        table_page_offsets: tablePageOffsets.value || {},
        table_selected_artifacts: selectedTableArtifactsByWorkspace.value || {},
        figure_selected_artifacts: selectedFigureArtifactsByWorkspace.value || {},
      },
      session: {
        active_workspace_id: activeWorkspaceId.value || '',
        active_conversation_id: activeConversationId.value || '',
        active_turn_id: activeTurnId.value || '',
        question_history: Array.isArray(questionHistory.value) ? questionHistory.value : [],
      },
      editor: {
        generated_code: generatedCode.value || '',
        python_file_content: pythonFileContent.value || '',
        user_edited_code: userEditedCode.value || '',
        has_user_edited_code: !!hasUserEditedCode.value,
        code_editor_source: codeEditorSource.value === 'user' ? 'user' : 'agent',
      }
    }
  }

  function applyLocalStateSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') return false
    const llm = snapshot.llm || {}
    const ui = snapshot.ui || {}
    const sessionState = snapshot.session || {}
    const editor = snapshot.editor || {}

    if (typeof llm.llm_provider === 'string' && llm.llm_provider.trim()) {
      llmProvider.value = llm.llm_provider.trim().toLowerCase()
    }
    const snapshotProvider = llmProvider.value || DEFAULT_PROVIDER
    if (Array.isArray(llm.provider_main_models)) {
      const restoredMainModels = normalizeModelList(llm.provider_main_models, snapshotProvider)
      if (restoredMainModels.length) {
        providerMainModels.value = restoredMainModels
      }
    }
    if (Array.isArray(llm.provider_lite_models)) {
      const restoredLiteModels = normalizeModelList(llm.provider_lite_models, snapshotProvider)
      if (restoredLiteModels.length) {
        providerLiteModels.value = restoredLiteModels
      }
    }
    if (providerMainModels.value.length) {
      availableModels.value = [...providerMainModels.value]
    }
    if (typeof llm.selected_model === 'string' && llm.selected_model.trim()) {
      selectedModel.value = llm.selected_model.trim()
    }
    if (!providerMainModels.value.includes(selectedModel.value)) {
      selectedModel.value = providerMainModels.value[0] || selectedModel.value
    }
    if (typeof llm.selected_lite_model === 'string' && llm.selected_lite_model.trim()) {
      selectedLiteModel.value = llm.selected_lite_model.trim()
    }
    if (!providerLiteModels.value.includes(selectedLiteModel.value)) {
      selectedLiteModel.value = providerLiteModels.value[0] || selectedLiteModel.value
    }
    selectedCodingModel.value = selectedModel.value || selectedCodingModel.value
    if (llm.slow_request_warning_seconds !== undefined && llm.slow_request_warning_seconds !== null) {
      slowRequestWarningSeconds.value = normalizeSlowRequestWarningSeconds(llm.slow_request_warning_seconds)
    }
    if (typeof llm.allow_llm_data_samples === 'boolean') {
      allowLlmDataSamples.value = llm.allow_llm_data_samples
    }

    if (typeof ui.active_tab === 'string' && ui.active_tab.trim()) {
      const restoredTab = ui.active_tab.trim().toLowerCase()
      if (restoredTab === 'code') {
        activeTab.value = 'workspace'
        workspacePane.value = 'code'
      } else if (restoredTab === 'chat') {
        activeTab.value = 'workspace'
        workspacePane.value = 'chat'
      } else if (restoredTab === 'ctree') {
        activeTab.value = 'workspace'
        workspacePane.value = 'chat'
      } else if (restoredTab === 'preview') {
        activeTab.value = 'workspace'
      } else {
        activeTab.value = restoredTab
      }
    }
    if (typeof ui.workspace_pane === 'string' && ui.workspace_pane.trim()) {
      workspacePane.value = normalizeWorkspacePane(ui.workspace_pane)
    }
    if (typeof ui.data_pane === 'string' && ui.data_pane.trim()) {
      dataPane.value = ['table', 'figure', 'output'].includes(ui.data_pane) ? ui.data_pane : 'table'
    }
    if (typeof ui.left_pane_width === 'number' && ui.left_pane_width > 10 && ui.left_pane_width < 90) {
      leftPaneWidth.value = ui.left_pane_width
    }
    if (typeof ui.terminal_open === 'boolean') {
      isTerminalOpen.value = ui.terminal_open
    }
    if (typeof ui.terminal_consent_granted === 'boolean') {
      terminalConsentGranted.value = ui.terminal_consent_granted
    }
    if (typeof ui.terminal_height === 'number' && ui.terminal_height >= 10 && ui.terminal_height <= 90) {
      terminalHeight.value = ui.terminal_height
    }
    if (typeof ui.is_sidebar_collapsed === 'boolean') {
      isSidebarCollapsed.value = ui.is_sidebar_collapsed
    }
    if (typeof ui.ui_theme === 'string' && ui.ui_theme.trim()) {
      uiTheme.value = normalizeThemeId(ui.ui_theme)
    }
    if (typeof ui.ui_font === 'string' && ui.ui_font.trim()) {
      uiFont.value = normalizeAppFontId(ui.ui_font)
    }
    if (typeof ui.ui_code_font === 'string' && ui.ui_code_font.trim()) {
      uiCodeFont.value = normalizeCodeFontId(ui.ui_code_font)
    }
    if (typeof ui.table_row_count === 'number' && ui.table_row_count >= 0) {
      tableRowCount.value = Math.max(0, Math.floor(ui.table_row_count))
    }
    if (typeof ui.table_window_start === 'number' && ui.table_window_start >= 0) {
      tableWindowStart.value = Math.max(0, Math.floor(ui.table_window_start))
    }
    if (typeof ui.table_window_end === 'number' && ui.table_window_end >= 0) {
      tableWindowEnd.value = Math.max(0, Math.floor(ui.table_window_end))
    }
    if (ui.table_page_offsets && typeof ui.table_page_offsets === 'object') {
      tablePageOffsets.value = { ...ui.table_page_offsets }
    }
    if (ui.table_selected_artifacts && typeof ui.table_selected_artifacts === 'object') {
      selectedTableArtifactsByWorkspace.value = { ...ui.table_selected_artifacts }
    }
    if (ui.figure_selected_artifacts && typeof ui.figure_selected_artifacts === 'object') {
      selectedFigureArtifactsByWorkspace.value = { ...ui.figure_selected_artifacts }
    }

    if (typeof sessionState.active_workspace_id === 'string') {
      activeWorkspaceId.value = sessionState.active_workspace_id
    }
    if (typeof sessionState.active_conversation_id === 'string') {
      activeConversationId.value = sessionState.active_conversation_id
    }
    if (typeof sessionState.active_turn_id === 'string') {
      activeTurnId.value = String(sessionState.active_turn_id || '').trim()
    }
    if (Array.isArray(sessionState.question_history)) {
      questionHistory.value = sessionState.question_history
        .map((item) => String(item || '').trim())
        .filter((item) => item.length > 0)
        .slice(-MAX_QUESTION_HISTORY)
    }
    if (typeof editor.generated_code === 'string') {
      generatedCode.value = editor.generated_code
    }
    if (typeof editor.user_edited_code === 'string') {
      userEditedCode.value = editor.user_edited_code
    }
    if (typeof editor.has_user_edited_code === 'boolean') {
      hasUserEditedCode.value = editor.has_user_edited_code
    } else {
      hasUserEditedCode.value = Boolean(userEditedCode.value && userEditedCode.value !== generatedCode.value)
    }
    if (typeof editor.code_editor_source === 'string') {
      codeEditorSource.value = editor.code_editor_source === 'user' ? 'user' : 'agent'
    }
    if (typeof editor.python_file_content === 'string') {
      pythonFileContent.value = editor.python_file_content
    } else if (typeof editor.generated_code === 'string') {
      pythonFileContent.value = editor.generated_code
    }
    if (!userEditedCode.value && hasUserEditedCode.value && pythonFileContent.value) {
      userEditedCode.value = pythonFileContent.value
    }

    return true
  }

  function schedulePreferenceSync() {
    if (suppressPreferenceSync) return
    const targetUserId = resolveSnapshotUserId()
    if (!authStore.isAuthenticated || !targetUserId) return
    if (preferenceSyncTimer) clearTimeout(preferenceSyncTimer)
    preferenceSyncTimer = setTimeout(async () => {
      await syncPreferencesNow(targetUserId)
    }, 150)
  }

  function saveLocalConfig() {
    schedulePreferenceSync()
    scheduleLocalSnapshotSave()
  }
  uiStore.configurePersistence(saveLocalConfig)
  preferencesStore.configurePersistence(saveLocalConfig)
  artifactStore.configurePersistence(scheduleLocalSnapshotSave)

  function scheduleLocalSnapshotSave() {
    const targetUserId = resolveSnapshotUserId()
    if (!authStore.isAuthenticated || !targetUserId) return
    const snapshot = buildLocalStateSnapshot()
    if (localStateSyncTimer) clearTimeout(localStateSyncTimer)
    localStateSyncTimer = setTimeout(() => {
      void localStateService.saveSnapshot(snapshot, targetUserId)
    }, 250)
  }

  async function flushLocalConfig(explicitUserId = null) {
    const targetUserId = resolveSnapshotUserId(explicitUserId)
    if (!targetUserId) return false
    if (preferenceSyncTimer) {
      clearTimeout(preferenceSyncTimer)
      preferenceSyncTimer = null
      await syncPreferencesNow(targetUserId)
    }
    if (localStateSyncTimer) {
      clearTimeout(localStateSyncTimer)
      localStateSyncTimer = null
    }
    await localStateService.saveSnapshot(buildLocalStateSnapshot(), targetUserId)
    return true
  }

  async function syncPreferencesNow(targetUserId) {
    const activeUserId = resolveSnapshotUserId()
    if (!authStore.isAuthenticated || !activeUserId || activeUserId !== targetUserId) return
    try {
      const response = await apiService.v1UpdatePreferences({
        llm_provider: llmProvider.value,
        selected_model: selectedModel.value,
        selected_lite_model: selectedLiteModel.value,
        selected_coding_model: selectedModel.value,
        slow_request_warning_seconds: normalizeSlowRequestWarningSeconds(slowRequestWarningSeconds.value),
        allow_llm_data_samples: allowLlmDataSamples.value,
      })
      applyPreferencesResponse(response)
    } catch (_error) {
      // Best-effort sync. Keep UI responsive even if backend is unavailable.
    }
  }

  async function loadLocalConfig(explicitUserId = null) {
    const targetUserId = resolveSnapshotUserId(explicitUserId)
    if (!targetUserId) return false
    const snapshot = await localStateService.loadSnapshot(targetUserId)
    if (!snapshot) return false
    return applyLocalStateSnapshot(snapshot)
  }

  function clearInMemoryUserState() {
    apiKey.value = ''
    apiKeyConfigured.value = false
    llmProvider.value = DEFAULT_PROVIDER
    availableProviders.value = [...DEFAULT_PROVIDER_LIST]
    selectedModel.value = 'google/gemini-2.5-flash'
    selectedLiteModel.value = DEFAULT_LITE_MODEL
    selectedCodingModel.value = 'google/gemini-2.5-flash'
    slowRequestWarningSeconds.value = DEFAULT_SLOW_REQUEST_WARNING_SECONDS
    availableModels.value = [...DEFAULT_MODELS]
    providerMainModels.value = [...DEFAULT_MODELS]
    providerLiteModels.value = [DEFAULT_LITE_MODEL]
    providerModelSearchResults.value = {}
    providerModelSearchLoading.value = false
    providerModelSearchQuery.value = ''
    providerModelCatalogs.value = {}
    providerRequiresApiKey.value = true
    apiKeyPresenceByProvider.value = {}
    selectedProviderApiKeyPresent.value = false
    columnCatalog.value = []
    uiTheme.value = DEFAULT_THEME_ID
    uiFont.value = DEFAULT_APP_FONT_ID
    uiCodeFont.value = DEFAULT_CODE_FONT_ID
    pythonFileContent.value = ''
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'

    chatHistory.value = []
    questionHistory.value = []
    currentQuestion.value = ''
    liveTokenUsage.value = null
    activeConversationUsage.value = null
    conversationUsageById.value = {}
    workspaces.value = []
    activeWorkspaceSummary.value = null
    workspaceAIConfig.value = null
    activeWorkspaceId.value = ''
    conversations.value = []
    activeConversationId.value = ''
    workspaceRuntimeStatusById.value = {}

    generatedCode.value = ''
    resultData.value = null
    plotlyFigure.value = null
    dataframes.value = []
    figures.value = []
    promotedUserDataframes.value = []
    promotedUserFigures.value = []
    dataframeCount.value = 0
    figureCount.value = 0
    tableRowCount.value = 0
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    tablePageOffsets.value = {}
    selectedTableArtifactsByWorkspace.value = {}
    selectedFigureArtifactsByWorkspace.value = {}
    dataPaneError.value = ''
    terminalOutput.value = ''
    terminalEntries.value = []
    terminalEntriesTrimmedCount.value = 0
    runtimeError.value = ''
    terminalConsentGranted.value = false
    terminalCwd.value = ''
    backgroundOperations.value = []
  }

  function clearPendingSyncTimers() {
    if (preferenceSyncTimer) {
      clearTimeout(preferenceSyncTimer)
      preferenceSyncTimer = null
    }
    if (localStateSyncTimer) {
      clearTimeout(localStateSyncTimer)
      localStateSyncTimer = null
    }
  }

  function resetForAuthBoundary() {
    clearPendingSyncTimers()
    ensuredRuntimeWorkspaceIds.clear()
    workspaceRuntimeStatusById.value = {}
    clearInMemoryUserState()
  }

  // Actions
  function setColumnCatalog(columns) {
    columnCatalog.value = Array.isArray(columns) ? columns : []
  }

  function setApiKey(key) {
    preferencesStore.setApiKey(key)
  }

  function setSelectedModel(model) {
    selectedModel.value = String(model || '').trim()
    selectedCodingModel.value = selectedModel.value
    mergeProviderModelOptions(llmProvider.value, [])
    saveLocalConfig()
  }

  async function searchProviderModels(query, limit = 25) {
    const provider = normalizeProviderName(llmProvider.value)
    const normalizedQuery = String(query || '').trim()
    providerModelSearchQuery.value = normalizedQuery

    if (normalizedQuery.length < 3) {
      providerModelSearchLoading.value = false
      return mergeProviderModelOptions(provider, [])
    }

    const cacheKey = providerModelSearchCacheKey(provider, normalizedQuery)
    const cached = providerModelSearchResults.value?.[cacheKey]
    if (Array.isArray(cached)) {
      return mergeProviderModelOptions(provider, cached)
    }

    const requestToken = ++providerModelSearchToken
    providerModelSearchLoading.value = true
    try {
      const response = await apiService.v1SearchProviderModels(provider, normalizedQuery, limit)
      if (requestToken !== providerModelSearchToken) {
        return mergeProviderModelOptions(provider, [])
      }
      const searchModels = normalizeSearchModelIds(response?.models, provider)
      providerModelSearchResults.value = {
        ...providerModelSearchResults.value,
        [cacheKey]: searchModels,
      }
      return mergeProviderModelOptions(provider, searchModels)
    } catch (_error) {
      if (requestToken === providerModelSearchToken) {
        return mergeProviderModelOptions(provider, [])
      }
      return mergeProviderModelOptions(provider, [])
    } finally {
      if (requestToken === providerModelSearchToken) {
        providerModelSearchLoading.value = false
      }
    }
  }

  function setUiTheme(themeId, options = {}) {
    preferencesStore.setUiTheme(themeId, options)
  }

  function setUiFont(fontId, options = {}) {
    preferencesStore.setUiFont(fontId, options)
  }

  function setUiCodeFont(fontId, options = {}) {
    preferencesStore.setUiCodeFont(fontId, options)
  }



  // Python File Management (simplified to single file)
  function setPythonFileContent(content) {
    pythonFileContent.value = content
    saveLocalConfig()
  }

  function resolveAgentCodeBaseline(fallbackCode = '') {
    const generated = String(generatedCode.value || '')
    if (generated) return generated

    const activeCode = String(activeTurnCode.value || '')
    if (activeCode) {
      generatedCode.value = activeCode
      return activeCode
    }

    const fallback = String(fallbackCode || '')
    if (fallback) {
      generatedCode.value = fallback
      return fallback
    }

    return ''
  }

  function noteUserEditedCode(content, options = {}) {
    const edited = String(content || '')
    const previousContent = String(options?.baselineCode || '')
    const baselineFallback = previousContent && previousContent !== edited ? previousContent : ''
    const agentCode = resolveAgentCodeBaseline(baselineFallback)
    userEditedCode.value = edited
    hasUserEditedCode.value = agentCode ? edited !== agentCode : Boolean(edited)
    codeEditorSource.value = hasUserEditedCode.value ? 'user' : 'agent'
    pythonFileContent.value = edited
    saveLocalConfig()
  }

  function createEmptyStreamTrace() {
    return {
      reasoning: [],
      planText: '',
      planNode: '',
      events: [],
      toolCalls: [],
      stopped: false,
      stoppedReason: ''
    }
  }

  function getLastChatMessage() {
    if (chatHistory.value.length === 0) return null
    return chatHistory.value[chatHistory.value.length - 1]
  }

  function ensureMessageStreamTrace(message) {
    if (!message || typeof message !== 'object') return null
    if (!message.streamTrace || typeof message.streamTrace !== 'object') {
      message.streamTrace = createEmptyStreamTrace()
    }
    if (!Array.isArray(message.streamTrace.events)) {
      message.streamTrace.events = []
    }
    if (!Array.isArray(message.streamTrace.reasoning)) {
      message.streamTrace.reasoning = []
    }
    if (typeof message.streamTrace.planText !== 'string') {
      message.streamTrace.planText = ''
    }
    if (typeof message.streamTrace.planNode !== 'string') {
      message.streamTrace.planNode = ''
    }
    if (!Array.isArray(message.streamTrace.toolCalls)) {
      message.streamTrace.toolCalls = []
    }
    if (typeof message.streamTrace.stopped !== 'boolean') {
      message.streamTrace.stopped = false
    }
    if (typeof message.streamTrace.stoppedReason !== 'string') {
      message.streamTrace.stoppedReason = ''
    }
    return message.streamTrace
  }

  function addChatMessage(question, explanation, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    const codeSnapshot = String(options?.codeSnapshot || '')
    const resultExplanation = String(options?.resultExplanation || explanation || '')
    const codeExplanation = String(options?.codeExplanation || '')
    const analysisMetadata = options?.analysisMetadata && typeof options.analysisMetadata === 'object'
      ? { ...options.analysisMetadata }
      : {}
    const attachments = Array.isArray(options?.attachments)
      ? options.attachments.map((item) => ({ ...item }))
      : []
    const streamTrace = options?.streamTrace && typeof options.streamTrace === 'object'
      ? {
        reasoning: Array.isArray(options.streamTrace.reasoning) ? options.streamTrace.reasoning : [],
        planText: String(options.streamTrace.planText || ''),
        planNode: String(options.streamTrace.planNode || ''),
        events: Array.isArray(options.streamTrace.events) ? options.streamTrace.events : [],
        toolCalls: Array.isArray(options.streamTrace.toolCalls) ? options.streamTrace.toolCalls : [],
        stopped: Boolean(options.streamTrace.stopped),
        stoppedReason: String(options.streamTrace.stoppedReason || '')
      }
      : createEmptyStreamTrace()

    // Add to local state
    const message = {
      id: options?.localMessageId || Date.now(),
      question,
      explanation: resultExplanation,
      resultExplanation,
      codeExplanation,
      analysisMetadata,
      attachments,
      streamTrace,
      codeSnapshot,
      codeUpdated: Boolean(codeSnapshot.trim()),
      toolEvents: Array.isArray(options?.toolEvents) ? options.toolEvents : null,
      timestamp: new Date().toISOString()
    }
    mutateConversationState(targetConversationId, (state, active) => {
      if (active) {
        chatHistory.value.push(message)
        currentQuestion.value = question
      } else {
        state.chatHistory = [...(state.chatHistory || []), message]
        state.currentQuestion = question
      }
    })
    return message.id
  }

  function addQuestionHistoryEntry(question) {
    const normalized = String(question || '').trim()
    if (!normalized) return

    const existing = Array.isArray(questionHistory.value) ? questionHistory.value : []
    if (existing[existing.length - 1] === normalized) return

    const next = [...existing, normalized]
    questionHistory.value = next.slice(-MAX_QUESTION_HISTORY)
    saveLocalConfig()
  }

  function getChatMessageById(messageId, options = {}) {
    const targetId = String(messageId || '').trim()
    if (!targetId) return null
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    if (!targetConversationId || isActiveConversation(targetConversationId)) {
      return chatHistory.value.find((message) => String(message?.id || '') === targetId) || null
    }
    const state = getConversationState(targetConversationId)
    return (state?.chatHistory || []).find((message) => String(message?.id || '') === targetId) || null
  }

  function getTargetChatMessage(messageId, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    const byId = getChatMessageById(messageId, { conversationId: targetConversationId })
    if (byId) return byId
    if (targetConversationId && !isActiveConversation(targetConversationId)) {
      const state = getConversationState(targetConversationId)
      const history = Array.isArray(state?.chatHistory) ? state.chatHistory : []
      return history[history.length - 1] || null
    }
    return getLastChatMessage()
  }

  function updateLastMessageExplanation(explanation, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      lastMessage.explanation = explanation
      lastMessage.resultExplanation = explanation
    })
  }

  function appendLastMessageExplanationChunk(text, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || typeof text !== 'string' || !text) return
      const current = String(lastMessage.explanation || '')
      const updated = current + text
      lastMessage.explanation = updated
      lastMessage.resultExplanation = updated
    })
  }

  function setLastMessageCodeExplanation(explanation, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      lastMessage.codeExplanation = String(explanation || '')
    })
  }

  function setLastMessageAnalysisMetadata(metadata, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      const normalized = metadata && typeof metadata === 'object' ? { ...metadata } : {}
      lastMessage.analysisMetadata = normalized
      if (normalized.token_usage && typeof normalized.token_usage === 'object') {
        syncLiveTokenUsageFromChatHistory({ conversationId: targetConversationId })
      }
    })
  }

  function toTokenUsageNumber(value) {
    const parsed = Number(value)
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
  }

  function mergeTokenUsageTotals(base, incoming) {
    return mergeUsageTotals(base, incoming)
  }

  function setLiveTokenUsage(usage) {
    if (!usage || typeof usage !== 'object') {
      liveTokenUsage.value = null
      return
    }
    const normalized = normalizeUsage(usage)
    liveTokenUsage.value = normalized ? { ...normalized } : null
  }

  function setLiveTokenUsageForCurrentTurn(usage, options = {}) {
    if (!usage || typeof usage !== 'object') return
    const conversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    const persistedUsage = conversationUsageById.value?.[conversationId]?.usage || resolveTokenUsageFromChatHistory({ excludeLast: true, conversationId })
    const merged = mergeTokenUsageTotals(persistedUsage, usage)
    if (isActiveConversation(conversationId)) {
      setLiveTokenUsage(merged)
      if (activeConversationUsage.value && typeof activeConversationUsage.value === 'object') {
        activeConversationUsage.value = {
          ...activeConversationUsage.value,
          usage: merged,
        }
      }
      syncActiveConversationState({ conversationId })
      return
    }
    const state = getConversationState(conversationId, { create: true })
    setConversationState(conversationId, {
      liveTokenUsage: merged,
      activeConversationUsage: state?.activeConversationUsage
        ? { ...state.activeConversationUsage, usage: merged }
        : state?.activeConversationUsage || null,
    })
  }

  function clearLiveTokenUsage() {
    liveTokenUsage.value = null
  }

  function clearActiveConversationUsage() {
    activeConversationUsage.value = null
  }

  function setActiveConversationUsage(summary) {
    const conversationId = String(summary?.conversation_id || activeConversationId.value || '').trim()
    if (!conversationId) {
      clearActiveConversationUsage()
      return
    }
    const normalized = {
      conversation_id: conversationId,
      turn_count: Number.isFinite(Number(summary?.turn_count)) ? Number(summary.turn_count) : 0,
      turns_with_usage: Number.isFinite(Number(summary?.turns_with_usage)) ? Number(summary.turns_with_usage) : 0,
      usage: normalizeUsage(summary?.usage) || {
        input_tokens: null,
        output_tokens: null,
        cached_tokens: null,
        total_tokens: null,
        price_usd: null,
      },
    }
    conversationUsageById.value = {
      ...(conversationUsageById.value || {}),
      [conversationId]: normalized,
    }
    if (conversationId === String(activeConversationId.value || '').trim()) {
      activeConversationUsage.value = normalized
      setLiveTokenUsage(normalized.usage)
    }
  }

  async function fetchActiveConversationUsage(conversationId = activeConversationId.value) {
    const targetConversationId = String(conversationId || '').trim()
    if (!targetConversationId) {
      clearActiveConversationUsage()
      clearLiveTokenUsage()
      return null
    }
    const summary = await apiService.v1GetConversationUsage(targetConversationId)
    setActiveConversationUsage(summary)
    return summary
  }

  function resolveTokenUsageFromChatHistory(options = {}) {
    const excludeLast = Boolean(options?.excludeLast)
    const conversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    const history = isActiveConversation(conversationId)
      ? chatHistory.value
      : (getConversationState(conversationId)?.chatHistory || [])
    if (!Array.isArray(history) || history.length === 0) return null
    let totals = null
    const end = excludeLast ? history.length - 1 : history.length
    for (let index = 0; index < end; index += 1) {
      const message = history[index]
      const metadata = message?.analysisMetadata
      const tokenUsage = metadata?.token_usage
      if (tokenUsage && typeof tokenUsage === 'object') {
        totals = mergeTokenUsageTotals(totals, tokenUsage)
      }
    }
    return totals
  }

  function resolveLatestTokenUsageFromChatHistory(options = {}) {
    return resolveTokenUsageFromChatHistory(options)
  }

  function syncLiveTokenUsageFromChatHistory(options = {}) {
    const conversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    const usage = resolveLatestTokenUsageFromChatHistory({ conversationId })
    if (isActiveConversation(conversationId)) {
      if (usage && typeof usage === 'object') {
        setLiveTokenUsage(usage)
      } else {
        clearLiveTokenUsage()
      }
      syncActiveConversationState({ conversationId })
      return
    }
    setConversationState(conversationId, {
      liveTokenUsage: usage && typeof usage === 'object' ? usage : null,
    })
  }

  function appendLastMessagePlanChunk(text, node = '', messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || typeof text !== 'string' || !text) return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      trace.planText += text
      if (node) trace.planNode = String(node)
    })
  }

  function appendLastMessageReasoningEvent(event, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || !event || typeof event !== 'object') return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      const message = String(event.message || '').trim()
      if (!message) return
      const stage = String(event.stage || 'intent').trim() || 'intent'
      const route = String(event.route || '').trim()
      const existing = trace.reasoning.find(
        (item) => String(item.stage || '') === stage && String(item.message || '') === message
      )
      if (existing) return
      trace.reasoning.push({
        stage,
        message,
        route,
        timestamp: new Date().toISOString(),
      })
    })
  }

  function appendLastMessageTraceEvent(event, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || !event || typeof event !== 'object') return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      trace.events.push({
        type: String(event.type || 'status'),
        node: String(event.node || ''),
        stage: String(event.stage || ''),
        message: String(event.message || event.node || ''),
        output: String(event.output || ''),
        timestamp: new Date().toISOString()
      })
    })
  }

  function markLastMessageStreamStopped(reason = 'Response generation stopped.', messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      trace.stopped = true
      trace.stoppedReason = String(reason || 'Response generation stopped.')
      trace.events.push({
        type: 'status',
        node: 'stream_control',
        stage: 'stopped',
        message: trace.stoppedReason,
        output: '',
        timestamp: new Date().toISOString()
      })
    })
  }

  function appendLastMessageToolCall(event, messageId = null) {
    const options = arguments[2] || {}
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || !event || typeof event !== 'object') return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      const callId = String(event.call_id || '')
      if (!callId) return
      const existing = trace.toolCalls.find((item) => String(item.call_id || '') === callId)
      if (existing) {
        existing.tool = String(event.tool || existing.tool || '')
        existing.args = event.args && typeof event.args === 'object' ? event.args : existing.args || {}
        existing.explanation = String(event.explanation || existing.explanation || '')
        if (!Array.isArray(existing.lines)) existing.lines = []
        existing.status = String(existing.status || 'running')
        return
      }
      trace.toolCalls.push({
        call_id: callId,
        tool: String(event.tool || ''),
        args: event.args && typeof event.args === 'object' ? event.args : {},
        explanation: String(event.explanation || ''),
        lines: [],
        output: null,
        status: 'running',
        duration_ms: null,
        started_at: new Date().toISOString(),
      })
    })
  }

  function appendLastMessageToolProgress(event, messageId = null) {
    const options = arguments[2] || {}
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || !event || typeof event !== 'object') return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      const callId = String(event.call_id || '')
      if (!callId) return
      const tool = trace.toolCalls.find((item) => String(item.call_id || '') === callId)
      if (!tool) return
      if (!Array.isArray(tool.lines)) tool.lines = []
      tool.lines.push(String(event.line || ''))
      if (tool.lines.length > 500) {
        tool.lines.splice(0, tool.lines.length - 500)
      }
    })
  }

  function appendLastMessageToolResult(event, messageId = null) {
    const options = arguments[2] || {}
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || !event || typeof event !== 'object') return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace) return
      const callId = String(event.call_id || '')
      if (!callId) return
      const tool = trace.toolCalls.find((item) => String(item.call_id || '') === callId)
      if (!tool) {
        trace.toolCalls.push({
          call_id: callId,
          tool: '',
          args: {},
          lines: [],
          output: event.output ?? null,
          status: String(event.status || 'success'),
          duration_ms: Number.isFinite(Number(event.duration_ms)) ? Number(event.duration_ms) : null,
          started_at: new Date().toISOString(),
        })
        return
      }
      tool.output = event.output ?? null
      tool.status = String(event.status || tool.status || 'success')
      tool.duration_ms = Number.isFinite(Number(event.duration_ms)) ? Number(event.duration_ms) : null
      tool.completed_at = new Date().toISOString()
    })
  }

  function setLastMessageCodeSnapshot(code, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      const codeSnapshot = String(code || '')
      lastMessage.codeSnapshot = codeSnapshot
      lastMessage.codeUpdated = Boolean(codeSnapshot.trim())
    })
  }

  function setLastMessageTurnId(turnId, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, (state, active) => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      const normalizedTurnId = String(turnId || '').trim()
      if (!normalizedTurnId) return
      lastMessage.id = normalizedTurnId
      if (active) {
        activeTurnId.value = normalizedTurnId
      } else {
        state.activeTurnId = normalizedTurnId
      }
    })
  }

  async function fetchColumnCatalog({ force = false } = {}) {
    const workspaceId = String(activeWorkspaceId.value || '').trim()
    if (!workspaceId) {
      columnCatalog.value = []
      return []
    }
    if (!force && Array.isArray(columnCatalog.value) && columnCatalog.value.length > 0) {
      return columnCatalog.value
    }
    try {
      const response = await apiService.v1ListDatasets(workspaceId)
      const datasets = Array.isArray(response?.datasets) ? response.datasets : []
      const schemaResults = await Promise.allSettled(
        datasets.map(async (dataset) => {
          const tableName = String(dataset?.table_name || '').trim()
          if (!tableName) return []
          const schema = await apiService.v1GetDatasetSchema(workspaceId, tableName)
          const schemaColumns = Array.isArray(schema?.columns) ? schema.columns : []
          return schemaColumns
            .map((column) => ({
              table_name: String(schema?.table_name || tableName).trim(),
              column_name: String(column?.name || column?.column_name || '').trim(),
              dtype: String(column?.dtype || column?.type || ''),
            }))
            .filter((column) => column.table_name && column.column_name)
        })
      )
      const columns = schemaResults
        .flatMap((result) => (result.status === 'fulfilled' ? result.value : []))
      columnCatalog.value = columns
      return columns
    } catch (_error) {
      columnCatalog.value = []
      return []
    }
  }

  function clearConversationScopedState(options = {}) {
    const preserveChatHistory = Boolean(options?.preserveChatHistory)
    activeTurnId.value = ''
    activeTurn.value = null
    activeTurnCode.value = ''
    activeTurnRelations.value = null
    finalTurnId.value = ''
    generatedCode.value = ''
    pythonFileContent.value = ''
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
    resultData.value = null
    plotlyFigure.value = null
    setDataframes([])
    setFigures([])
    dataframeCount.value = 0
    tableRowCount.value = 0
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    if (activeWorkspaceId.value) {
      setSelectedTableArtifact(activeWorkspaceId.value, '')
      setSelectedFigureArtifact(activeWorkspaceId.value, '')
    }
    terminalOutput.value = ''
    dataPaneError.value = ''
    if (!preserveChatHistory) {
      chatHistory.value = []
    }
    clearLiveTokenUsage()
    if (!preserveChatHistory) {
      clearActiveConversationUsage()
    }
  }

  function setActiveConversationId(conversationId) {
    const previousConversationId = normalizeConversationId(activeConversationId.value)
    if (previousConversationId) {
      syncActiveConversationState({ conversationId: previousConversationId })
    }
    const nextConversationId = normalizeConversationId(conversationId)
    activeConversationId.value = nextConversationId
    activeTab.value = 'workspace'
    workspacePane.value = 'chat'
    if (!nextConversationId) {
      clearConversationScopedState()
      saveLocalConfig()
      return
    }
    const existingState = getConversationState(nextConversationId, { create: true })
    applyConversationStateToActive(nextConversationId, existingState)
    const cachedUsage = conversationUsageById.value?.[nextConversationId]
    if (cachedUsage) {
      activeConversationUsage.value = cachedUsage
      setLiveTokenUsage(cachedUsage.usage)
    } else if (!existingState?.activeConversationUsage) {
      clearActiveConversationUsage()
    }
    saveLocalConfig()
  }

  function setActiveTurnId(turnId) {
    activeTurnId.value = String(turnId || '').trim()
    saveLocalConfig()
  }

  function setActiveTurnPayload(turn) {
    activeTurn.value = turn && typeof turn === 'object' ? { ...turn } : null
    activeTurnCode.value = String(turn?.code_snapshot || '')
    generatedCode.value = activeTurnCode.value
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
    setPythonFileContent(activeTurnCode.value)
  }

  function hydrateArtifactsFromToolEvents(toolEvents) {
    const normalizedEvents = Array.isArray(toolEvents) ? toolEvents : []
    const dataframeArtifacts = []
    const figureArtifacts = []

    for (const event of normalizedEvents) {
      if (!event || typeof event !== 'object' || String(event.type || '') !== 'artifact') continue
      const artifact = event.data
      if (!artifact || typeof artifact !== 'object') continue

      const kind = String(artifact.kind || '').toLowerCase()
      const logicalName = String(artifact.logical_name || kind || 'artifact')

      if (kind === 'dataframe') {
        dataframeArtifacts.push({
          name: logicalName || 'dataframe',
          data: {
            artifact_id: artifact?.artifact_id || null,
            logical_name: artifact?.logical_name || logicalName || undefined,
            display_name: artifact?.display_name || artifact?.logical_name || logicalName || undefined,
            row_count: Number(artifact?.row_count || 0),
            columns: Array.isArray(artifact?.schema)
              ? artifact.schema.map((col) => String(col?.name || '')).filter(Boolean)
              : [],
            data: Array.isArray(artifact?.preview_rows) ? artifact.preview_rows : [],
            created_at: String(artifact?.created_at || ''),
          }
        })
        continue
      }

      if (kind === 'figure') {
        const figure = normalizePlotlyFigure(artifact?.payload?.figure ?? artifact?.payload)
        if (!figure) continue
        figureArtifacts.push({
          name: logicalName || 'figure',
          artifact_id: artifact?.artifact_id || null,
          created_at: String(artifact?.created_at || ''),
          data: figure,
        })
      }
    }

    setDataframes(dataframeArtifacts)
    setFigures(figureArtifacts)

    const workspaceId = String(activeWorkspaceId.value || '').trim()
    if (workspaceId) {
      setSelectedTableArtifact(workspaceId, dataframeArtifacts[0]?.data?.artifact_id || '')
      setSelectedFigureArtifact(workspaceId, figureArtifacts[0]?.artifact_id || '')
    }

    if (figureArtifacts.length > 0) {
      setPlotlyFigure(figureArtifacts[0].data)
      setResultData(null)
      revealArtifactsPane({ hasFigures: true })
      return
    }
    if (dataframeArtifacts.length > 0) {
      setResultData(dataframeArtifacts[0].data)
      setPlotlyFigure(null)
      revealArtifactsPane({ hasDataframes: true })
      return
    }
    setResultData(null)
    setPlotlyFigure(null)
  }

  function setActiveTurnRelations(payload) {
    activeTurnRelations.value = payload && typeof payload === 'object' ? { ...payload } : null
    hydrateArtifactsFromToolEvents(payload?.current?.tool_events)
    activeTurnArtifactRefreshKey.value += 1
  }

  function setWorkspaceTurnTree(payload) {
    workspaceTurnTree.value = payload && typeof payload === 'object' ? { ...payload } : null
  }

  async function loadActiveTurnRelations(turnId = activeTurnId.value) {
    const conversationId = String(activeConversationId.value || '').trim()
    const targetTurnId = String(turnId || '').trim()
    if (!conversationId || !targetTurnId) return null
    const relations = await apiService.v1GetTurnRelations(conversationId, targetTurnId)
    setActiveTurnId(targetTurnId)
    setActiveTurnPayload(relations?.current || null)
    setActiveTurnRelations(relations)
    return relations
  }

  async function loadWorkspaceTurnTree(workspaceId = activeWorkspaceId.value) {
    const targetWorkspaceId = String(workspaceId || '').trim()
    if (!targetWorkspaceId) {
      setWorkspaceTurnTree(null)
      return null
    }
    const payload = await apiService.v1GetWorkspaceTurnTree(targetWorkspaceId)
    setWorkspaceTurnTree(payload)
    return payload
  }

  async function deleteTurn(turnId, conversationId = activeConversationId.value) {
    const targetConversationId = String(conversationId || '').trim()
    const targetTurnId = String(turnId || '').trim()
    if (!targetConversationId || !targetTurnId) return null
    await apiService.v1DeleteTurn(targetConversationId, targetTurnId)
    const nextConversationStates = { ...(conversationStateById.value || {}) }
    delete nextConversationStates[targetConversationId]
    conversationStateById.value = nextConversationStates
    await fetchConversations()
    const isActiveConversation = targetConversationId === String(activeConversationId.value || '').trim()
    const conversationStillExists = conversations.value.some(
      (conversation) => String(conversation?.id || '').trim() === targetConversationId
    )
    if (isActiveConversation && conversationStillExists) {
      await fetchConversationTurns()
    } else if (isActiveConversation) {
      const fallbackConversationId = String(conversations.value[0]?.id || '').trim()
      setActiveConversationId(fallbackConversationId)
      if (fallbackConversationId) {
        await fetchConversationTurns()
      } else {
        clearConversationScopedState()
      }
    }
    await loadWorkspaceTurnTree()
    return true
  }

  async function loadFinalTurn(conversationId = activeConversationId.value) {
    const targetConversationId = String(conversationId || '').trim()
    if (!targetConversationId) {
      finalTurnId.value = ''
      return null
    }
    const turn = await apiService.v1GetFinalTurn(targetConversationId)
    finalTurnId.value = String(turn?.id || '').trim()
    return turn
  }

  async function goToPreviousTurn() {
    const previousTurnId = String(activeTurnRelations.value?.previous_turn?.id || '').trim()
    if (!previousTurnId) return null
    return loadActiveTurnRelations(previousTurnId)
  }

  async function goToNextTurn() {
    const nextTurnId = String(activeTurnRelations.value?.next_turn?.id || '').trim()
    if (!nextTurnId) return null
    return loadActiveTurnRelations(nextTurnId)
  }

  async function markTurnFinal(turnId, conversationId = activeConversationId.value) {
    const targetConversationId = String(conversationId || '').trim()
    const targetTurnId = String(turnId || '').trim()
    if (!targetConversationId || !targetTurnId) return null
    const turn = await apiService.v1MarkFinalTurn(targetConversationId, targetTurnId)
    if (targetConversationId === String(activeConversationId.value || '').trim()) {
      finalTurnId.value = String(turn?.id || '').trim()
      await loadActiveTurnRelations(targetTurnId)
      await fetchActiveConversationUsage(targetConversationId)
    }
    await loadWorkspaceTurnTree()
    return turn
  }

  function prependChatHistoryFromTurns(turns) {
    if (!Array.isArray(turns) || turns.length === 0) return
    const mapped = turns.map((turn) => ({
      id: turn.id,
      question: turn.user_text,
      explanation: turn.assistant_text,
      resultExplanation: String(turn?.metadata?.result_explanation || turn.assistant_text || ''),
      codeExplanation: String(turn?.metadata?.code_explanation || ''),
      analysisMetadata: turn?.metadata && typeof turn.metadata === 'object' ? { ...turn.metadata } : {},
      attachments: Array.isArray(turn?.metadata?.user_attachments) ? turn.metadata.user_attachments.map((item) => ({ ...item })) : [],
      toolEvents: turn.tool_events || null,
      streamTrace: null,
      codeSnapshot: turn.code_snapshot || '',
      codeUpdated: Boolean(String(turn.code_snapshot || '').trim()),
      timestamp: turn.created_at || new Date().toISOString()
    }))
    chatHistory.value = [...mapped.reverse(), ...chatHistory.value]
    rehydrateArtifactsFromChatHistory()
    syncLiveTokenUsageFromChatHistory()
  }

  function rehydrateArtifactsFromChatHistory() {
    const dataframeArtifacts = []
    const figureArtifacts = []
    const seenDataframes = new Set()
    const seenFigures = new Set()

    for (const message of chatHistory.value) {
      const toolEvents = Array.isArray(message?.toolEvents) ? message.toolEvents : []
      for (const event of toolEvents) {
        if (!event || typeof event !== 'object' || String(event.type || '') !== 'artifact') continue
        const artifact = event.data
        if (!artifact || typeof artifact !== 'object') continue

        const kind = String(artifact.kind || '').toLowerCase()
        const artifactId = String(artifact.artifact_id || '').trim()
        const logicalName = String(artifact.logical_name || kind || 'artifact')
        const dedupeKey = artifactId || `${kind}:${logicalName}:${String(artifact.created_at || '')}`

        if (kind === 'dataframe') {
          if (seenDataframes.has(dedupeKey)) continue
          seenDataframes.add(dedupeKey)
          dataframeArtifacts.push({
            name: logicalName || 'dataframe',
            data: {
              artifact_id: artifactId || null,
              row_count: Number(artifact.row_count || 0),
              columns: Array.isArray(artifact.schema)
                ? artifact.schema.map((col) => String(col?.name || '')).filter(Boolean)
                : [],
              data: []
            }
          })
          continue
        }

        if (kind === 'figure') {
          if (seenFigures.has(dedupeKey)) continue
          seenFigures.add(dedupeKey)
          const figurePayload = normalizePlotlyFigure(artifact?.payload?.figure ?? artifact?.payload)
          if (figurePayload) {
            figureArtifacts.push({
              name: logicalName || 'figure',
              artifact_id: artifactId || null,
              data: figurePayload,
            })
          }
          continue
        }

      }
    }

    setDataframes(dataframeArtifacts)
    setFigures(figureArtifacts)
    if (figureArtifacts.length > 0) {
      setPlotlyFigure(figureArtifacts[0].data)
      revealArtifactsPane({ hasFigures: true })
    } else if (dataframeArtifacts.length > 0) {
      setResultData(dataframeArtifacts[0].data)
      revealArtifactsPane({ hasDataframes: true })
    }
  }

  async function fetchWorkspaces() {
    const response = await workspaceService.list()
    const items = response?.workspaces || []
    workspaces.value = items
    if (!activeWorkspaceId.value && items.length > 0) {
      const active = items.find((w) => w.is_active) || items[0]
      activeWorkspaceId.value = active.id
      saveLocalConfig()
    }
    if (activeWorkspaceId.value && !items.some((ws) => ws.id === activeWorkspaceId.value)) {
      activeWorkspaceId.value = items[0]?.id || ''
      activeConversationId.value = ''
      chatHistory.value = []
      clearLiveTokenUsage()
      columnCatalog.value = []
      saveLocalConfig()
    }

    if (activeWorkspaceId.value) {
      await Promise.all([
        fetchActiveWorkspaceSummary(activeWorkspaceId.value),
        fetchWorkspaceAIConfig(activeWorkspaceId.value),
      ])
    } else {
      activeWorkspaceSummary.value = null
      workspaceAIConfig.value = null
      columnCatalog.value = []
    }

  }

  async function fetchActiveWorkspaceSummary(workspaceId = activeWorkspaceId.value) {
    const target = String(workspaceId || '').trim()
    if (!target) {
      activeWorkspaceSummary.value = null
      return null
    }
    try {
      const summary = await workspaceService.summary(target)
      if (target === activeWorkspaceId.value) activeWorkspaceSummary.value = summary
      return summary
    } catch (_error) {
      if (target === activeWorkspaceId.value) activeWorkspaceSummary.value = null
      return null
    }
  }

  async function fetchWorkspaceAIConfig(workspaceId = activeWorkspaceId.value) {
    const target = String(workspaceId || '').trim()
    if (!target) {
      workspaceAIConfig.value = null
      return null
    }
    const config = await apiService.v1GetWorkspaceAIConfig(target)
    if (target === activeWorkspaceId.value) workspaceAIConfig.value = config
    return config
  }

  async function saveWorkspaceAIConfig(payload, workspaceId = activeWorkspaceId.value) {
    const target = String(workspaceId || '').trim()
    if (!target) throw new Error('Select a workspace before updating AI settings.')
    const config = await apiService.v1UpdateWorkspaceAIConfig(target, payload)
    if (target === activeWorkspaceId.value) workspaceAIConfig.value = config
    return config
  }

  async function createWorkspace(name, schemaContext = '') {
    const ws = await workspaceService.create(name, schemaContext)
    if (ws?.id) {
      await activateWorkspace(ws.id)
    }
    await fetchWorkspaces()
    return ws
  }

  async function activateWorkspace(workspaceId) {
    await workspaceService.activate(workspaceId)
    activeWorkspaceId.value = workspaceId
    workspaces.value = workspaces.value.map((workspace) => ({
      ...workspace,
      is_active: workspace.id === workspaceId,
    }))
    conversations.value = []
    activeConversationId.value = ''
    chatHistory.value = []
    clearLiveTokenUsage()
    activeWorkspaceSummary.value = null
    workspaceAIConfig.value = null
    columnCatalog.value = []
    saveLocalConfig()
    await Promise.all([
      fetchActiveWorkspaceSummary(workspaceId),
      fetchWorkspaceAIConfig(workspaceId),
    ])
  }

  async function renameWorkspace(workspaceId, name, schemaContext = undefined) {
    const updated = await workspaceService.update(workspaceId, name, schemaContext)
    const idx = workspaces.value.findIndex((ws) => ws.id === workspaceId)
    if (idx >= 0) {
      workspaces.value[idx] = { ...workspaces.value[idx], ...updated }
    }
    saveLocalConfig()
    return updated
  }

  async function fetchConversations() {
    if (!activeWorkspaceId.value) return
    const response = await apiService.v1ListConversations(activeWorkspaceId.value, 50)
    conversations.value = response?.conversations || []

    const currentActiveId = String(activeConversationId.value || '').trim()
    if (!currentActiveId) {
      if (conversations.value.length > 0) {
        setActiveConversationId(conversations.value[0].id)
      }
      return
    }

    const conversationIds = new Set(
      conversations.value
        .map((conversation) => String(conversation?.id || '').trim())
        .filter(Boolean),
    )
    if (!conversationIds.has(currentActiveId)) {
      setActiveConversationId(conversations.value[0]?.id || '')
    }
  }

  async function createConversation(title = null) {
    if (!activeWorkspaceId.value) return null
    const conv = await apiService.v1CreateConversation(activeWorkspaceId.value, title)
    await fetchConversations()
    setActiveConversationId(conv.id)
    clearConversationScopedState()
    await loadWorkspaceTurnTree()
    saveLocalConfig()
    return conv
  }

  async function ensureActiveConversation(title = null) {
    const workspaceId = String(activeWorkspaceId.value || '').trim()
    if (!workspaceId) return null
    const currentId = String(activeConversationId.value || '').trim()
    if (currentId) return currentId

    const conv = await apiService.v1CreateConversation(workspaceId, title)
    const conversationId = String(conv?.id || '').trim()
    if (!conversationId) return null

    const existing = Array.isArray(conversations.value) ? conversations.value : []
    const withoutDuplicate = existing.filter((item) => String(item?.id || '') !== conversationId)
    conversations.value = [conv, ...withoutDuplicate]
    setActiveConversationId(conversationId)
    await fetchConversations()
    await loadWorkspaceTurnTree()
    saveLocalConfig()
    return conversationId
  }

  async function fetchConversationTurns({ preferLatest = false } = {}) {
    const targetConversationId = normalizeConversationId(activeConversationId.value)
    if (!targetConversationId) return
    const cachedState = getConversationState(targetConversationId)
    if (
      isConversationRunning(targetConversationId) &&
      Array.isArray(cachedState?.chatHistory) &&
      cachedState.chatHistory.length > 0
    ) {
      applyConversationStateToActive(targetConversationId, cachedState)
      return
    }
    const preferredTurnId = String(activeTurnId.value || '').trim()
    const response = await apiService.v1ListTurns(targetConversationId, 5)
    const turns = response?.turns || []
    chatHistory.value = []
    clearLiveTokenUsage()
    prependChatHistoryFromTurns(turns)
    await fetchActiveConversationUsage(targetConversationId)
    const newestTurnId = String(turns[0]?.id || '').trim()
    const targetTurnId = preferLatest ? newestTurnId : (preferredTurnId || newestTurnId)
    if (targetTurnId) {
      try {
        await loadActiveTurnRelations(targetTurnId)
      } catch (_error) {
        if (newestTurnId && newestTurnId !== targetTurnId) {
          await loadActiveTurnRelations(newestTurnId)
        } else {
          setActiveTurnId('')
          setActiveTurnPayload(null)
          setActiveTurnRelations(null)
        }
      }
    } else {
      clearConversationScopedState()
    }
    await loadFinalTurn(targetConversationId)
    syncActiveConversationState({ conversationId: targetConversationId })
  }

  async function deleteConversationById(conversationId) {
    const targetId = String(conversationId || '').trim()
    if (!targetId) return ''

    await apiService.v1DeleteConversation(targetId)
    conversations.value = conversations.value.filter((conversation) => String(conversation?.id || '').trim() !== targetId)
    const usageMap = { ...(conversationUsageById.value || {}) }
    delete usageMap[targetId]
    conversationUsageById.value = usageMap

    const currentActiveId = String(activeConversationId.value || '').trim()
    const activeStillExists = currentActiveId
      ? conversations.value.some((conversation) => String(conversation?.id || '').trim() === currentActiveId)
      : false

    if (activeStillExists) {
      await loadWorkspaceTurnTree()
      return targetId
    }

    const fallbackConversationId = String(conversations.value[0]?.id || '').trim()
    if (currentActiveId !== fallbackConversationId) {
      setActiveConversationId(fallbackConversationId)
    } else {
      saveLocalConfig()
    }

    clearConversationScopedState()

    if (fallbackConversationId) {
      await fetchConversationTurns()
    } else {
      clearConversationScopedState()
    }
    await loadWorkspaceTurnTree()

    return targetId
  }

  async function updateConversationTitle(title) {
    if (!activeConversationId.value) return
    const updated = await apiService.v1UpdateConversation(activeConversationId.value, title)
    // Update local list
    const idx = conversations.value.findIndex(c => c.id === activeConversationId.value)
    if (idx !== -1) {
      conversations.value[idx] = { ...conversations.value[idx], title: updated.title }
    }
    return updated
  }

  async function deleteWorkspaceAsync(workspaceId) {
    const result = await workspaceService.delete(workspaceId)
    setSelectedTableArtifact(workspaceId, '')
    setSelectedFigureArtifact(workspaceId, '')
    if (activeWorkspaceId.value === workspaceId) {
      activeWorkspaceId.value = ''
      activeConversationId.value = ''
      chatHistory.value = []
      clearLiveTokenUsage()
      columnCatalog.value = []
      saveLocalConfig()
    }
    return result
  }

  function setGeneratedCode(code) {
    const generated = String(code || '')
    generatedCode.value = generated
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
    saveLocalConfig()
  }

  function setCodeEditorSource(source) {
    const normalized = source === 'user' ? 'user' : 'agent'
    const agentCode = resolveAgentCodeBaseline()
    codeEditorSource.value = normalized
    pythonFileContent.value = normalized === 'user'
      ? String(userEditedCode.value || '')
      : agentCode
    saveLocalConfig()
  }

  function setResultData(data) {
    artifactStore.setResultData(data)
  }

  function setPlotlyFigure(figure) {
    artifactStore.setPlotlyFigure(figure)
  }

  function selectDataPaneForArtifacts({ hasFigures = false, hasDataframes = false, hasOutput = false } = {}) {
    if (hasFigures) {
      setDataPane('figure')
      return 'figure'
    }
    if (hasDataframes) {
      setDataPane('table')
      return 'table'
    }
    if (hasOutput) {
      setDataPane('output')
      return 'output'
    }
    return dataPane.value
  }

  function producedOutputFlags(payload = {}) {
    return {
      hasFigures: payload?.hasFigures === true,
      hasDataframes: payload?.hasDataframes === true,
      hasOutput: payload?.hasOutput === true,
    }
  }

  function revealArtifactsPane(payload = {}) {
    const { hasFigures, hasDataframes, hasOutput } = producedOutputFlags(payload)
    if (!hasFigures && !hasDataframes && !hasOutput) return dataPane.value
    return selectDataPaneForArtifacts({ hasFigures, hasDataframes, hasOutput })
  }

  function setDataframes(dfs) {
    artifactStore.setDataframes(dfs)
  }

  function setFigures(figs) {
    artifactStore.setFigures(figs)
  }

  function setScalars(items) {
    artifactStore.setScalars(items)
  }

  function currentResultScopeKey() {
    const conversationId = String(activeConversationId.value || '').trim()
    if (conversationId) return `conversation:${conversationId}`
    const workspaceId = String(activeWorkspaceId.value || '').trim()
    return workspaceId ? `workspace:${workspaceId}` : 'workspace:unscoped'
  }

  function promotedArtifactId(prefix, runId, outputId) {
    const safe = `${runId || 'run'}-${outputId || 'output'}`
      .replace(/[^a-zA-Z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '')
    return `${prefix}-${safe || Date.now().toString(36)}`
  }

  function promoteUserRunTable(output, options = {}) {
    if (!output || typeof output !== 'object') return ''
    const runId = String(options?.runId || output?.runId || output?.run_id || '').trim()
    const outputId = String(options?.outputId || output?.id || options?.index || '1').trim()
    const artifactId = promotedArtifactId('user-table', runId, outputId)
    const existing = promotedUserDataframes.value.find((item) => (
      String(item?.data?.artifact_id || item?.artifact_id || '').trim() === artifactId
    ))
    const workspaceId = String(activeWorkspaceId.value || '').trim()
    if (existing) {
      if (workspaceId) setSelectedTableArtifact(workspaceId, artifactId)
      setResultData(existing.data)
      setDataPane('table')
      return artifactId
    }

    const rawData = output?.data && typeof output.data === 'object' ? output.data : output
    const sourceArtifactId = String(rawData?.artifact_id || output?.artifact_id || '').trim()
    const logicalName = String(
      rawData?.logical_name || output?.logical_name || output?.name || `user_table_${promotedUserDataframes.value.length + 1}`,
    ).trim()
    const displayName = `User revision · ${String(rawData?.display_name || output?.display_name || logicalName).trim()}`
    const supersedesArtifactId = workspaceId ? getSelectedTableArtifact(workspaceId) : ''
    const promoted = {
      ...output,
      name: logicalName,
      origin: 'user',
      promoted: true,
      scopeKey: currentResultScopeKey(),
      sourceRunId: runId,
      supersedes_artifact_id: supersedesArtifactId || undefined,
      data: {
        ...rawData,
        artifact_id: artifactId,
        source_artifact_id: sourceArtifactId || undefined,
        logical_name: logicalName,
        display_name: displayName,
      },
    }
    promotedUserDataframes.value = [promoted, ...promotedUserDataframes.value]
    if (workspaceId) setSelectedTableArtifact(workspaceId, artifactId)
    setResultData(promoted.data)
    setDataPane('table')
    syncActiveConversationState()
    return artifactId
  }

  function promoteUserRunFigure(output, options = {}) {
    if (!output || typeof output !== 'object') return ''
    const runId = String(options?.runId || output?.runId || output?.run_id || '').trim()
    const outputId = String(options?.outputId || output?.id || options?.index || '1').trim()
    const artifactId = promotedArtifactId('user-chart', runId, outputId)
    const existing = promotedUserFigures.value.find((item) => (
      String(item?.artifact_id || item?.data?.artifact_id || '').trim() === artifactId
    ))
    const workspaceId = String(activeWorkspaceId.value || '').trim()
    if (existing) {
      if (workspaceId) setSelectedFigureArtifact(workspaceId, artifactId)
      setPlotlyFigure(existing.data)
      setDataPane('figure')
      return artifactId
    }

    const rawFigure = normalizePlotlyFigure(output?.data ?? output)
    if (!rawFigure) return ''
    const logicalName = String(output?.logical_name || output?.name || `user_chart_${promotedUserFigures.value.length + 1}`).trim()
    const displayName = `User revision · ${String(output?.display_name || logicalName).trim()}`
    const supersedesArtifactId = workspaceId ? getSelectedFigureArtifact(workspaceId) : ''
    const promoted = {
      ...output,
      name: logicalName,
      artifact_id: artifactId,
      logical_name: logicalName,
      display_name: displayName,
      origin: 'user',
      promoted: true,
      scopeKey: currentResultScopeKey(),
      sourceRunId: runId,
      supersedes_artifact_id: supersedesArtifactId || undefined,
      data: rawFigure,
    }
    promotedUserFigures.value = [promoted, ...promotedUserFigures.value]
    if (workspaceId) setSelectedFigureArtifact(workspaceId, artifactId)
    setPlotlyFigure(promoted.data)
    setDataPane('figure')
    syncActiveConversationState()
    return artifactId
  }

  function removeResultArtifact(artifactId) {
    artifactStore.removeResultArtifact(artifactId)
  }

  function setDataframeCount(count) {
    artifactStore.setDataframeCount(count)
  }

  function setFigureCount(count) {
    artifactStore.setFigureCount(count)
  }

  function setDataPaneError(msg) {
    artifactStore.setDataPaneError(msg)
  }

  function clearDataPaneError() {
    artifactStore.clearDataPaneError()
  }

  function setTableViewport(start, end, total) {
    artifactStore.setTableViewport(start, end, total)
  }

  function clearTableViewport() {
    artifactStore.clearTableViewport()
  }

  function tableOffsetKey(workspaceId, artifactId) {
    const workspaceKey = String(workspaceId || '').trim()
    const artifactKey = String(artifactId || '').trim()
    const turnKey = String(activeTurnId.value || '').trim()
    return `${workspaceKey}::${turnKey || 'workspace'}::${artifactKey}`
  }

  function workspaceSelectionKey(workspaceId) {
    const workspaceKey = String(workspaceId || '').trim()
    const turnKey = String(activeTurnId.value || '').trim()
    if (!workspaceKey) return ''
    return `${workspaceKey}::${turnKey || 'workspace'}`
  }

  function setTablePageOffset(workspaceId, artifactId, page) {
    artifactStore.setTablePageOffset(workspaceId, artifactId, page, activeTurnId.value)
  }

  function getTablePageOffset(workspaceId, artifactId) {
    return artifactStore.getTablePageOffset(workspaceId, artifactId, activeTurnId.value)
  }

  function setSelectedTableArtifact(workspaceId, artifactId) {
    artifactStore.setSelectedTableArtifact(workspaceId, artifactId, activeTurnId.value)
  }

  function getSelectedTableArtifact(workspaceId) {
    return artifactStore.getSelectedTableArtifact(workspaceId, activeTurnId.value)
  }

  function setSelectedFigureArtifact(workspaceId, artifactId) {
    artifactStore.setSelectedFigureArtifact(workspaceId, artifactId, activeTurnId.value)
  }

  function getSelectedFigureArtifact(workspaceId) {
    return artifactStore.getSelectedFigureArtifact(workspaceId, activeTurnId.value)
  }

  function setTerminalOutput(output) {
    terminalOutput.value = output
  }

  function setRuntimeError(message) {
    runtimeError.value = String(message || '')
  }

  function normalizeWorkspaceRuntimeStatus(status) {
    const normalized = String(status || '').trim().toLowerCase()
    if (['ready', 'busy', 'starting', 'connecting', 'error', 'missing'].includes(normalized)) {
      return normalized
    }
    return 'missing'
  }

  function setWorkspaceRuntimeStatus(workspaceId, status) {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return
    const normalizedStatus = normalizeWorkspaceRuntimeStatus(status)

    const currentStatus = String(workspaceRuntimeStatusById.value?.[normalizedWorkspaceId] || '').trim()
    if (currentStatus === normalizedStatus) {
      if (normalizedStatus === 'ready' || normalizedStatus === 'busy') {
        ensuredRuntimeWorkspaceIds.add(normalizedWorkspaceId)
      } else {
        ensuredRuntimeWorkspaceIds.delete(normalizedWorkspaceId)
      }
      return
    }

    workspaceRuntimeStatusById.value = {
      ...workspaceRuntimeStatusById.value,
      [normalizedWorkspaceId]: normalizedStatus
    }

    if (normalizedStatus === 'ready' || normalizedStatus === 'busy') {
      ensuredRuntimeWorkspaceIds.add(normalizedWorkspaceId)
      if (
        ['ready', 'busy'].includes(normalizedStatus) &&
        normalizedWorkspaceId === String(activeWorkspaceId.value || '').trim()
      ) {
        setRuntimeError('')
      }
      return
    }

    ensuredRuntimeWorkspaceIds.delete(normalizedWorkspaceId)
  }

  function getWorkspaceRuntimeStatus(workspaceId = activeWorkspaceId.value) {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return 'missing'
    return normalizeWorkspaceRuntimeStatus(workspaceRuntimeStatusById.value?.[normalizedWorkspaceId] || 'missing')
  }

  function trimTerminalStream(text, maxChars = MAX_TERMINAL_STREAM_CHARS) {
    const normalized = String(text || '')
    if (normalized.length <= maxChars) return normalized
    const droppedChars = normalized.length - maxChars
    return `${normalized.slice(0, maxChars)}\n[truncated ${droppedChars} chars]`
  }

  function normalizeTerminalEntryStatus(status) {
    const normalized = String(status || '').trim().toLowerCase()
    if (['running', 'success', 'error'].includes(normalized)) return normalized
    return 'success'
  }

  function terminalEntryCharSize(entry) {
    if (!entry || typeof entry !== 'object') return 0
    const scalarChars = Array.isArray(entry.scalarOutputs)
      ? entry.scalarOutputs.reduce((sum, item) => (
          sum
          + String(item?.name || '').length
          + String(item?.display_value ?? item?.value ?? '').length
        ), 0)
      : 0
    const structuredChars = [...(Array.isArray(entry.tableOutputs) ? entry.tableOutputs : []), ...(Array.isArray(entry.chartOutputs) ? entry.chartOutputs : [])]
      .reduce((sum, item) => {
        try {
          return sum + JSON.stringify(item).length
        } catch (_error) {
          return sum + String(item?.name || '').length
        }
      }, 0)
    return (
      String(entry.command || '').length +
      String(entry.stdout || '').length +
      String(entry.stderr || '').length +
      String(entry.label || '').length +
      scalarChars +
      structuredChars +
      32
    )
  }

  function enforceTerminalEntryLimits() {
    let trimmed = 0
    while (terminalEntries.value.length > MAX_TERMINAL_ENTRIES) {
      terminalEntries.value.shift()
      trimmed += 1
    }

    let totalChars = terminalEntries.value.reduce((sum, item) => sum + terminalEntryCharSize(item), 0)
    while (totalChars > MAX_TERMINAL_TOTAL_CHARS && terminalEntries.value.length > 1) {
      const removed = terminalEntries.value.shift()
      totalChars -= terminalEntryCharSize(removed)
      trimmed += 1
    }

    if (trimmed > 0) {
      terminalEntriesTrimmedCount.value += trimmed
    }
  }

  function appendTerminalEntry(entry) {
    if (!entry || typeof entry !== 'object') return
    const kind = entry.kind === 'output' ? 'output' : 'command'
    const stdout = trimTerminalStream(entry.stdout)
    const stderr = trimTerminalStream(entry.stderr)
    const normalizedEntry = {
      id: String(entry.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`),
      kind,
      source: String(entry.source || (kind === 'output' ? 'analysis' : 'terminal')),
      origin: ['user', 'ai', 'system'].includes(String(entry.origin || '').trim().toLowerCase())
        ? String(entry.origin).trim().toLowerCase()
        : (kind === 'command' ? 'system' : ''),
      conversationId: String(entry.conversationId || ''),
      label: String(entry.label || (kind === 'output' ? 'Python output' : '')),
      command: String(entry.command || ''),
      stdout,
      stderr,
      exitCode: Number.isInteger(entry.exitCode) ? entry.exitCode : 0,
      runId: String(entry.runId || ''),
      scalarOutputs: Array.isArray(entry.scalarOutputs)
        ? entry.scalarOutputs.map((item) => ({ ...(item || {}) }))
        : [],
      tableOutputs: Array.isArray(entry.tableOutputs)
        ? entry.tableOutputs.map((item) => ({ ...(item || {}) }))
        : [],
      chartOutputs: Array.isArray(entry.chartOutputs)
        ? entry.chartOutputs.map((item) => ({ ...(item || {}) }))
        : [],
      hasTableOutput: Boolean(entry.hasTableOutput),
      hasChartOutput: Boolean(entry.hasChartOutput),
      truncated: Boolean(entry.truncated),
      status: normalizeTerminalEntryStatus(
        entry.status || (kind === 'output' ? (stderr.trim() ? 'error' : 'success') : 'success')
      ),
      durationMs: Number.isFinite(Number(entry.durationMs)) ? Math.max(0, Number(entry.durationMs)) : null,
      createdAt: entry.createdAt || new Date().toISOString(),
      updatedAt: entry.updatedAt || new Date().toISOString(),
    }
    terminalEntries.value.push(normalizedEntry)
    enforceTerminalEntryLimits()
    return normalizedEntry.id
  }

  function updateTerminalEntry(entryId, patch = {}) {
    const targetId = String(entryId || '').trim()
    if (!targetId || !patch || typeof patch !== 'object') return false
    const index = terminalEntries.value.findIndex((item) => String(item?.id || '') === targetId)
    if (index < 0) return false

    const current = terminalEntries.value[index] || {}
    const kind = patch.kind === 'output'
      ? 'output'
      : (patch.kind === 'command' ? 'command' : (current.kind === 'output' ? 'output' : 'command'))

    const stdout = patch.stdout !== undefined
      ? trimTerminalStream(patch.stdout)
      : String(current.stdout || '')
    const stderr = patch.stderr !== undefined
      ? trimTerminalStream(patch.stderr)
      : String(current.stderr || '')

    terminalEntries.value[index] = {
      ...current,
      kind,
      source: patch.source !== undefined
        ? String(patch.source || (kind === 'output' ? 'analysis' : 'terminal'))
        : String(current.source || (kind === 'output' ? 'analysis' : 'terminal')),
      origin: patch.origin !== undefined
        ? (['user', 'ai', 'system'].includes(String(patch.origin || '').trim().toLowerCase())
            ? String(patch.origin).trim().toLowerCase()
            : '')
        : String(current.origin || ''),
      conversationId: patch.conversationId !== undefined
        ? String(patch.conversationId || '')
        : String(current.conversationId || ''),
      label: patch.label !== undefined
        ? String(patch.label || (kind === 'output' ? 'Run output' : ''))
        : String(current.label || (kind === 'output' ? 'Run output' : '')),
      command: patch.command !== undefined ? String(patch.command || '') : String(current.command || ''),
      stdout,
      stderr,
      exitCode: Number.isInteger(patch.exitCode)
        ? patch.exitCode
        : (Number.isInteger(current.exitCode) ? current.exitCode : 0),
      runId: patch.runId !== undefined ? String(patch.runId || '') : String(current.runId || ''),
      scalarOutputs: patch.scalarOutputs !== undefined
        ? (Array.isArray(patch.scalarOutputs) ? patch.scalarOutputs.map((item) => ({ ...(item || {}) })) : [])
        : (Array.isArray(current.scalarOutputs) ? current.scalarOutputs : []),
      tableOutputs: patch.tableOutputs !== undefined
        ? (Array.isArray(patch.tableOutputs) ? patch.tableOutputs.map((item) => ({ ...(item || {}) })) : [])
        : (Array.isArray(current.tableOutputs) ? current.tableOutputs : []),
      chartOutputs: patch.chartOutputs !== undefined
        ? (Array.isArray(patch.chartOutputs) ? patch.chartOutputs.map((item) => ({ ...(item || {}) })) : [])
        : (Array.isArray(current.chartOutputs) ? current.chartOutputs : []),
      hasTableOutput: patch.hasTableOutput !== undefined
        ? Boolean(patch.hasTableOutput)
        : Boolean(current.hasTableOutput),
      hasChartOutput: patch.hasChartOutput !== undefined
        ? Boolean(patch.hasChartOutput)
        : Boolean(current.hasChartOutput),
      truncated: patch.truncated !== undefined ? Boolean(patch.truncated) : Boolean(current.truncated),
      status: patch.status !== undefined
        ? normalizeTerminalEntryStatus(patch.status)
        : normalizeTerminalEntryStatus(current.status || (stderr.trim() ? 'error' : 'success')),
      durationMs: patch.durationMs !== undefined
        ? (Number.isFinite(Number(patch.durationMs)) ? Math.max(0, Number(patch.durationMs)) : null)
        : (Number.isFinite(Number(current.durationMs)) ? Math.max(0, Number(current.durationMs)) : null),
      createdAt: patch.createdAt || current.createdAt || new Date().toISOString(),
      updatedAt: patch.updatedAt || new Date().toISOString(),
    }
    enforceTerminalEntryLimits()
    return true
  }

  function removeTerminalEntry(entryId) {
    const targetId = String(entryId || '').trim()
    if (!targetId) return false
    const previousLength = terminalEntries.value.length
    terminalEntries.value = terminalEntries.value.filter(
      (entry) => String(entry?.id || '').trim() !== targetId,
    )
    if (terminalEntries.value.length === previousLength) return false
    return true
  }

  function setActiveTab(tab) {
    uiStore.setActiveTab(tab)
  }
  function setWorkspacePane(pane) {
    uiStore.setWorkspacePane(pane)
  }
  function setDataPane(pane) {
    uiStore.setDataPane(pane)
  }
  function setLeftPaneWidth(widthPct) {
    uiStore.setLeftPaneWidth(widthPct)
  }

  function setTerminalHeight(heightPct) {
    uiStore.setTerminalHeight(heightPct)
  }

  function toggleTerminal() {
    uiStore.toggleTerminal()
  }

  function setTerminalConsentGranted(granted) {
    uiStore.setTerminalConsentGranted(granted)
  }
  function setTerminalCwd(cwd) {
    uiStore.setTerminalCwd(cwd)
  }
  function setSidebarCollapsed(collapsed) {
    uiStore.setSidebarCollapsed(collapsed)
  }

  function openKeyboardShortcuts() {
    uiStore.openKeyboardShortcuts()
  }

  function closeKeyboardShortcuts() {
    uiStore.closeKeyboardShortcuts()
  }

  function openCommandPalette() {
    uiStore.openCommandPalette()
  }

  function closeCommandPalette() {
    uiStore.closeCommandPalette()
  }

  function toggleCommandPalette() {
    uiStore.toggleCommandPalette()
  }

  // Editor tracking
  function setEditorPosition(line, col) {
    uiStore.setEditorPosition(line, col)
  }
  function setEditorFocused(focused) {
    uiStore.setEditorFocused(focused)
  }

  function setLoading(loading) {
    uiStore.setLoading(loading)
  }

  function normalizeOperationPayload(payload = {}) {
    const now = Date.now()
    const id = String(payload?.id || `${payload?.type || 'operation'}-${now}-${Math.random().toString(36).slice(2, 8)}`).trim()
    return {
      id,
      type: String(payload?.type || 'operation').trim(),
      title: String(payload?.title || 'Working').trim(),
      message: String(payload?.message || '').trim(),
      status: String(payload?.status || 'running').trim(),
      progress: Number.isFinite(Number(payload?.progress)) ? Math.max(0, Math.min(100, Number(payload.progress))) : null,
      priority: Number.isFinite(Number(payload?.priority)) ? Number(payload.priority) : 0,
      createdAt: Number(payload?.createdAt || now),
      updatedAt: now,
    }
  }

  function startBackgroundOperation(payload = {}) {
    return executionStore.startBackgroundOperation(payload)
  }

  function updateBackgroundOperation(operationId, payload = {}) {
    const id = String(operationId || '').trim()
    if (!id) return
    backgroundOperations.value = backgroundOperations.value.map((item) => {
      if (String(item?.id || '') !== id) return item
      return {
        ...item,
        ...payload,
        progress: Number.isFinite(Number(payload?.progress))
          ? Math.max(0, Math.min(100, Number(payload.progress)))
          : item.progress,
        updatedAt: Date.now(),
      }
    })
  }

  function removeBackgroundOperation(operationId) {
    const id = String(operationId || '').trim()
    if (!id) return
    backgroundOperations.value = backgroundOperations.value.filter((item) => String(item?.id || '') !== id)
  }

  function finishBackgroundOperation(operationId, payload = {}) {
    executionStore.finishBackgroundOperation(operationId, payload)
  }

  function isConversationRunning(conversationId) {
    return executionStore.isConversationRunning(conversationId)
  }

  function setConversationRun(conversationId, runState = null) {
    executionStore.setConversationRun(conversationId, runState)
  }

  function clearConversationRun(conversationId) {
    setConversationRun(conversationId, null)
  }

  function getConversationRun(conversationId) {
    return executionStore.getConversationRun(conversationId)
  }

  function abortConversationRun(conversationId) {
    return executionStore.abortConversationRun(conversationId)
  }

  function setCodeRunning(running) {
    executionStore.setCodeRunning(running)
  }

  function resetSession() {
    chatHistory.value = []
    liveTokenUsage.value = null
    activeConversationUsage.value = null
    conversationUsageById.value = {}
    currentQuestion.value = ''
    generatedCode.value = ''
    pythonFileContent.value = ''
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
    resultData.value = null
    plotlyFigure.value = null
    promotedUserDataframes.value = []
    promotedUserFigures.value = []
    terminalOutput.value = ''
    terminalEntries.value = []
    terminalEntriesTrimmedCount.value = 0
    runtimeError.value = ''
    tableRowCount.value = 0
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    tablePageOffsets.value = {}
    selectedTableArtifactsByWorkspace.value = {}
    selectedFigureArtifactsByWorkspace.value = {}
    activeTab.value = 'workspace'
    workspacePane.value = 'chat'
    dataPane.value = 'table'
    leftPaneWidth.value = 50
    isTerminalOpen.value = false
    terminalConsentGranted.value = false
    terminalCwd.value = ''
    isCodeRunning.value = false
    backgroundOperations.value = []
    columnCatalog.value = []
    workspaceRuntimeStatusById.value = {}
    ensuredRuntimeWorkspaceIds.clear()
    saveLocalConfig()
  }

  function applyPreferencesResponse(prefs) {
    const previousProvider = llmProvider.value
    if (typeof prefs?.llm_provider === 'string' && prefs.llm_provider.trim()) {
      llmProvider.value = prefs.llm_provider.trim().toLowerCase()
    }
    if (Array.isArray(prefs?.available_providers) && prefs.available_providers.length) {
      availableProviders.value = prefs.available_providers
    }
    if (Array.isArray(prefs?.provider_available_main_models) && prefs.provider_available_main_models.length) {
      providerMainModels.value = normalizeModelList(prefs.provider_available_main_models, llmProvider.value)
    }
    if (Array.isArray(prefs?.provider_available_lite_models) && prefs.provider_available_lite_models.length) {
      providerLiteModels.value = normalizeModelList(prefs.provider_available_lite_models, llmProvider.value)
    }
    if (prefs?.provider_model_catalogs && typeof prefs.provider_model_catalogs === 'object') {
      providerModelCatalogs.value = prefs.provider_model_catalogs
    }
    if (prefs?.api_key_present_by_provider && typeof prefs.api_key_present_by_provider === 'object') {
      apiKeyPresenceByProvider.value = prefs.api_key_present_by_provider
    }
    if (typeof prefs?.selected_provider_requires_api_key === 'boolean') {
      providerRequiresApiKey.value = prefs.selected_provider_requires_api_key
    }
    if (typeof prefs?.selected_provider_api_key_present === 'boolean') {
      selectedProviderApiKeyPresent.value = prefs.selected_provider_api_key_present
    }
    const responseProvider = llmProvider.value || DEFAULT_PROVIDER
    const fallbackMainModels = normalizeModelList(prefs?.provider_available_main_models, responseProvider)
    const legacyAvailableModels = normalizeModelList(prefs?.available_models, responseProvider)
    const legacyEnabledModels = normalizeModelList(prefs?.enabled_models, responseProvider)
    if (fallbackMainModels.length) {
      providerMainModels.value = fallbackMainModels
    } else if (legacyAvailableModels.length) {
      providerMainModels.value = legacyAvailableModels
    } else if (legacyEnabledModels.length) {
      providerMainModels.value = legacyEnabledModels
    }
    if (prefs?.selected_model) selectedModel.value = prefs.selected_model
    if (!providerMainModels.value.includes(selectedModel.value)) {
      selectedModel.value = providerMainModels.value[0] || 'google/gemini-2.5-flash'
    }
    if (prefs?.selected_lite_model) {
      selectedLiteModel.value = prefs.selected_lite_model
    }
    if (!providerLiteModels.value.includes(selectedLiteModel.value)) {
      selectedLiteModel.value = providerLiteModels.value[0] || DEFAULT_LITE_MODEL
    }
    selectedCodingModel.value = selectedModel.value
    if (prefs?.slow_request_warning_seconds !== undefined && prefs?.slow_request_warning_seconds !== null) {
      slowRequestWarningSeconds.value = normalizeSlowRequestWarningSeconds(
        prefs.slow_request_warning_seconds
      )
    }
    if (typeof prefs?.allow_llm_data_samples === 'boolean') {
      allowLlmDataSamples.value = prefs.allow_llm_data_samples
    }
    if (typeof prefs?.api_key_present === 'boolean') {
      apiKeyConfigured.value = prefs.api_key_present
    }
    const providerChanged = previousProvider !== llmProvider.value
    clearProviderModelSearchState()
    if (providerChanged) {
      providerModelSearchQuery.value = ''
    }
    mergeProviderModelOptions(llmProvider.value, [])

  }

  async function loadUserPreferences() {
    try {
      suppressPreferenceSync = true
      const prefs = await apiService.v1GetPreferences()
      applyPreferencesResponse(prefs)
    } catch (_error) {
      // Continue with defaults if preference fetch fails.
    } finally {
      suppressPreferenceSync = false
    }
  }

  return {
    // State
    columnCatalog,
    llmProvider,
    availableProviders,
    selectedModel,
    selectedLiteModel,
    selectedCodingModel,
    slowRequestWarningSeconds,
    availableModels,
    providerMainModels,
    providerLiteModels,
    providerModelSearchLoading,
    providerModelCatalogs,
    providerRequiresApiKey,
    apiKeyPresenceByProvider,
    selectedProviderApiKeyPresent,
    apiKey,
    apiKeyConfigured,
    schemaContext,
    allowLlmDataSamples,
    uiTheme,
    availableThemes,
    uiFont,
    availableFonts,
    uiCodeFont,
    availableCodeFonts,
    pythonFileContent,
    userEditedCode,
    hasUserEditedCode,
    codeEditorSource,
    chatHistory,
    questionHistory,
    currentQuestion,
    liveTokenUsage,
    activeConversationUsage,
    workspaces,
    activeWorkspaceSummary,
    workspaceAIConfig,
    activeWorkspaceId,
    conversations,
    activeConversationId,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnRelations,
    activeTurnArtifactRefreshKey,
    workspaceTurnTree,
    finalTurnId,
    generatedCode,
    resultData,
    plotlyFigure,
    dataframes,
    figures,
    scalars,
    promotedUserDataframes,
    promotedUserFigures,
    dataframeCount,
    tableRowCount,
    tableWindowStart,
    tableWindowEnd,
    dataPaneError,
    figureCount,
    terminalOutput,
    terminalEntries,
    terminalEntriesTrimmedCount,
    runtimeError,
    activeTab,
    workspacePane,
    dataPane,
    leftPaneWidth,
    isTerminalOpen,
    terminalHeight,
    terminalConsentGranted,
    terminalCwd,
    isSidebarCollapsed,
    isKeyboardShortcutsOpen,
    isCommandPaletteOpen,
    connectionFlowRequestId,
    editorLine,
    editorCol,
    isEditorFocused,
    isLoading,
    activeConversationIsLoading,
    runningConversationCount,
    isCodeRunning,
    activeBackgroundOperations,
    primaryBackgroundOperation,

    // Computed
    canAnalyze,
    hasWorkspace,
    workspaceReadiness,
    activeWorkspaceRuntimeStatus,

    // Primary UX flows
    openDataConnectionFlow,

    // Actions
    loadLocalConfig,
    flushLocalConfig,
    resetForAuthBoundary,
    setColumnCatalog,
    setApiKey,
    setSelectedModel,
    searchProviderModels,
    mergeProviderModelOptions,
    clearProviderModelSearchState,
    setUiTheme,
    setUiFont,
    setUiCodeFont,
    setPythonFileContent,
    noteUserEditedCode,
    setCodeEditorSource,
    addChatMessage,
    addQuestionHistoryEntry,
    updateLastMessageExplanation,
    setLastMessageCodeExplanation,
    setLastMessageAnalysisMetadata,
    setLiveTokenUsageForCurrentTurn,
    fetchActiveConversationUsage,
    syncLiveTokenUsageFromChatHistory,
    patchConversationState,
    appendLastMessageExplanationChunk,
    appendLastMessagePlanChunk,
    appendLastMessageReasoningEvent,
    appendLastMessageTraceEvent,
    appendLastMessageToolCall,
    appendLastMessageToolProgress,
    appendLastMessageToolResult,
    markLastMessageStreamStopped,
    setLastMessageCodeSnapshot,
    setLastMessageTurnId,
    setActiveConversationId,
    ensureActiveConversation,
    loadActiveTurnRelations,
    loadWorkspaceTurnTree,
    deleteTurn,
    loadFinalTurn,
    goToPreviousTurn,
    goToNextTurn,
    markTurnFinal,
    fetchWorkspaces,
    fetchActiveWorkspaceSummary,
    fetchWorkspaceAIConfig,
    saveWorkspaceAIConfig,
    fetchColumnCatalog,
    createWorkspace,
    deleteWorkspaceAsync,
    activateWorkspace,
    renameWorkspace,
    fetchConversations,
    createConversation,
    fetchConversationTurns,
    deleteConversationById,
    updateConversationTitle,
    setGeneratedCode,
    setResultData,
    setPlotlyFigure,
    setDataframes,
    setFigures,
    setScalars,
    promoteUserRunTable,
    promoteUserRunFigure,
    removeResultArtifact,
    setDataframeCount,
    setTableViewport,
    clearTableViewport,
    setTablePageOffset,
    getTablePageOffset,
    setSelectedTableArtifact,
    getSelectedTableArtifact,
    setSelectedFigureArtifact,
    getSelectedFigureArtifact,
    setFigureCount,
    setDataPaneError,
    clearDataPaneError,
    setTerminalOutput,
    setRuntimeError,
    setWorkspaceRuntimeStatus,
    getWorkspaceRuntimeStatus,
    appendTerminalEntry,
    updateTerminalEntry,
    removeTerminalEntry,
    setActiveTab,
    setWorkspacePane,
    setDataPane,
    revealArtifactsPane,
    setLeftPaneWidth,
    setTerminalHeight,
    toggleTerminal,
    setTerminalConsentGranted,
    setTerminalCwd,
    setSidebarCollapsed,
    openKeyboardShortcuts,
    closeKeyboardShortcuts,
    openCommandPalette,
    closeCommandPalette,
    toggleCommandPalette,
    setEditorPosition,
    setEditorFocused,
    applyPreferencesResponse,
    loadUserPreferences,
    setLoading,
    startBackgroundOperation,
    finishBackgroundOperation,
    isConversationRunning,
    setConversationRun,
    clearConversationRun,
    getConversationRun,
    abortConversationRun,
    setCodeRunning,
    resetSession,
    isSettingsOpen,
    settingsInitialTab,
    openSettings
  }
})
