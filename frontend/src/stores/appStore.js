import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { apiService } from '../services/apiService'
import { localStateService } from '../services/localStateService'
import { useAuthStore } from './authStore'
import { normalizePlotlyFigure } from '../utils/figurePayload'
import { DEFAULT_THEME_ID, THEME_OPTIONS, normalizeThemeId } from '../constants/themes'

export const useAppStore = defineStore('app', () => {
  const authStore = useAuthStore()
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

  // Files
  const dataFilePath = ref('')
  const schemaFilePath = ref('')
  const schemaFileId = ref('')
  const isSchemaFileUploaded = ref(false)
  const ingestedTableName = ref('')
  const ingestedColumns = ref([])
  const columnCatalog = ref([])
  const profileData = ref(null)

  // LLM Configuration
  const llmProvider = ref(DEFAULT_PROVIDER)
  const availableProviders = ref([...DEFAULT_PROVIDER_LIST])
  const selectedModel = ref('google/gemini-2.5-flash')
  const selectedLiteModel = ref(DEFAULT_LITE_MODEL)
  const selectedCodingModel = ref('google/gemini-2.5-flash')
  const slowRequestWarningSeconds = ref(DEFAULT_SLOW_REQUEST_WARNING_SECONDS)
  const availableModels = ref([...DEFAULT_MODELS])
  const providerMainModels = ref([...DEFAULT_MODELS])
  const providerLiteModels = ref([DEFAULT_LITE_MODEL])
  const providerModelSearchResults = ref({})
  const providerModelSearchLoading = ref(false)
  const providerModelSearchQuery = ref('')
  const providerModelCatalogs = ref({})
  const providerRequiresApiKey = ref(true)
  const apiKeyPresenceByProvider = ref({})
  const selectedProviderApiKeyPresent = ref(false)
  const apiKey = ref('')
  const apiKeyConfigured = ref(false)

  // Schema Context
  const schemaContext = ref('')
  const allowSchemaSampleValues = ref(false)
  const allowLlmDataSamples = ref(false)
  const plotlyThemeMode = ref('soft')
  const uiTheme = ref(DEFAULT_THEME_ID)
  const availableThemes = THEME_OPTIONS.map((theme) => ({ ...theme }))


  // Single Python File per Session (simplified)
  const pythonFileContent = ref('')

  // Chat
  const chatHistory = ref([])
  const questionHistory = ref([])
  const currentQuestion = ref('')
  const currentExplanation = ref('')
  const liveTokenUsage = ref(null)
  const workspaces = ref([])
  const workspaceDeletionJobs = ref([])
  const activeWorkspaceId = ref('')
  const conversations = ref([])
  const activeConversationId = ref('')
  const turnViewEnabled = ref(true)
  const activeTurnId = ref('')
  const activeTurn = ref(null)
  const activeTurnCode = ref('')
  const activeTurnArtifacts = ref([])
  const activeTurnRelations = ref(null)
  const finalTurnId = ref('')
  const turnsNextCursor = ref(null)
  const workspaceKernelStatusById = ref({})

  // Wasm Execution State
  const historicalCodeBlocks = ref([]) // Tracks successfully executed code snippets

  // Analysis
  const generatedCode = ref('')
  const resultData = ref(null)
  const plotlyFigure = ref(null)
  const dataframes = ref([])
  const figures = ref([])
  const dataframeCount = ref(0)
  const tableRowCount = ref(0)
  const tableWindowStart = ref(0)
  const tableWindowEnd = ref(0)
  const tablePageOffsets = ref({})
  const selectedTableArtifactsByWorkspace = ref({})
  const selectedFigureArtifactsByWorkspace = ref({})
  const dataPaneError = ref('')
  const figureCount = ref(0)
  const terminalOutput = ref('')
  const terminalEntries = ref([])
  const terminalEntriesTrimmedCount = ref(0)
  const terminalEnabled = ref(false)
  const runtimeError = ref('')
  const activeTab = ref('workspace')
  const workspacePane = ref('chat') // 'code' | 'chat'
  const dataPane = ref('table') // 'table' | 'figure' | 'output'
  const leftPaneWidth = ref(50) // percentage
  const terminalConsentGranted = ref(false)
  const isTerminalOpen = ref(false)
  const terminalHeight = ref(30) // percentage
  const terminalCwd = ref('')
  const isChatOverlayOpen = ref(true)
  const chatOverlayWidth = ref(0.25) // 25% of area
  const isSidebarCollapsed = ref(false)
  const workspaceLayoutMode = ref('chat') // 'chat' | 'split' | 'data'
  const hideShortcutsModal = ref(false)

  // Editor State
  const editorLine = ref(1)
  const editorCol = ref(1)
  const isEditorFocused = ref(false)

  // UI State
  const isLoading = ref(false)
  const isCodeRunning = ref(false)

  // Settings trigger - removed, no longer needed

  // Computed
  const hasDataFile = computed(() => dataFilePath.value.trim() !== '')
  const hasSchemaFile = computed(() => schemaFilePath.value.trim() !== '' || isSchemaFileUploaded.value)
  const hasWorkspace = computed(() => {
    const activeId = activeWorkspaceId.value.trim()
    if (!activeId) return false
    return workspaces.value.some((ws) => ws.id === activeId)
  })
  const isDataFocusMode = computed(() => workspaceLayoutMode.value === 'data')
  const showLeftPane = computed(() => workspaceLayoutMode.value !== 'data')
  const showRightPane = computed(() => workspaceLayoutMode.value !== 'chat')
  const canAnalyze = computed(() => {
    const hasProviderAccess = providerRequiresApiKey.value
      ? selectedProviderApiKeyPresent.value
      : true
    if (!hasProviderAccess) return false
    return hasWorkspace.value
  })
  const activeWorkspaceKernelStatus = computed(() => getWorkspaceKernelStatus())

  let preferenceSyncTimer = null
  let localStateSyncTimer = null
  let suppressPreferenceSync = false
  let kernelEnsureWorkspaceId = ''
  let kernelEnsurePromise = null
  let providerModelSearchToken = 0
  const ensuredKernelWorkspaceIds = new Set()
  const LOCAL_SNAPSHOT_VERSION = 1
  const MAX_TERMINAL_ENTRIES = 50
  const MAX_TERMINAL_STREAM_CHARS = 200000
  const MAX_TERMINAL_TOTAL_CHARS = 2000000
  const MAX_QUESTION_HISTORY = 30

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
        active_tab: activeTab.value || 'workspace',
        workspace_pane: workspacePane.value || 'chat',
        data_pane: dataPane.value || 'table',
        left_pane_width: Number(leftPaneWidth.value || 50),
        chat_overlay_open: !!isChatOverlayOpen.value,
        chat_overlay_width: Number(chatOverlayWidth.value || 0.25),
        terminal_open: !!isTerminalOpen.value,
        terminal_height: Number(terminalHeight.value || 30),
        is_sidebar_collapsed: !!isSidebarCollapsed.value,
        workspace_layout_mode: workspaceLayoutMode.value || 'chat',
        data_focus_mode: workspaceLayoutMode.value === 'data',
        hide_shortcuts_modal: !!hideShortcutsModal.value,
        table_row_count: Number(tableRowCount.value || 0),
        table_window_start: Number(tableWindowStart.value || 0),
        table_window_end: Number(tableWindowEnd.value || 0),
        table_page_offsets: tablePageOffsets.value || {},
        table_selected_artifacts: selectedTableArtifactsByWorkspace.value || {},
        figure_selected_artifacts: selectedFigureArtifactsByWorkspace.value || {},
      },
      session: {
        active_workspace_id: activeWorkspaceId.value || '',
        active_dataset_path: dataFilePath.value || '',
        active_table_name: ingestedTableName.value || '',
        active_conversation_id: activeConversationId.value || '',
        question_history: Array.isArray(questionHistory.value) ? questionHistory.value : [],
        schema_file_id: schemaFileId.value || '',
        schema_uploaded: !!isSchemaFileUploaded.value,
      },
      editor: {
        generated_code: generatedCode.value || '',
        python_file_content: pythonFileContent.value || ''
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
      } else if (restoredTab === 'preview') {
        activeTab.value = 'workspace'
      } else {
        activeTab.value = restoredTab
      }
    }
    if (typeof ui.workspace_pane === 'string' && ui.workspace_pane.trim()) {
      workspacePane.value = ui.workspace_pane === 'chat' ? 'chat' : 'code'
    }
    if (typeof ui.data_pane === 'string' && ui.data_pane.trim()) {
      dataPane.value = ['table', 'figure', 'output'].includes(ui.data_pane) ? ui.data_pane : 'table'
    }
    if (typeof ui.left_pane_width === 'number' && ui.left_pane_width > 10 && ui.left_pane_width < 90) {
      leftPaneWidth.value = ui.left_pane_width
    }
    if (typeof ui.chat_overlay_open === 'boolean') {
      isChatOverlayOpen.value = ui.chat_overlay_open
    }
    if (typeof ui.chat_overlay_width === 'number' && ui.chat_overlay_width > 0.1 && ui.chat_overlay_width < 0.9) {
      chatOverlayWidth.value = ui.chat_overlay_width
    }
    if (typeof ui.terminal_open === 'boolean') {
      isTerminalOpen.value = ui.terminal_open
    }
    if (typeof ui.terminal_height === 'number' && ui.terminal_height >= 10 && ui.terminal_height <= 90) {
      terminalHeight.value = ui.terminal_height
    }
    if (typeof ui.is_sidebar_collapsed === 'boolean') {
      isSidebarCollapsed.value = ui.is_sidebar_collapsed
    }
    if (typeof ui.workspace_layout_mode === 'string' && ui.workspace_layout_mode.trim()) {
      const restoredMode = ui.workspace_layout_mode.trim().toLowerCase()
      workspaceLayoutMode.value = ['chat', 'split', 'data'].includes(restoredMode) ? restoredMode : 'chat'
    } else if (typeof ui.data_focus_mode === 'boolean') {
      workspaceLayoutMode.value = ui.data_focus_mode ? 'data' : 'split'
    }
    if (typeof ui.hide_shortcuts_modal === 'boolean') {
      hideShortcutsModal.value = ui.hide_shortcuts_modal
    }
    if (typeof ui.ui_theme === 'string' && ui.ui_theme.trim()) {
      uiTheme.value = normalizeThemeId(ui.ui_theme)
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
    if (typeof sessionState.active_dataset_path === 'string') {
      dataFilePath.value = sessionState.active_dataset_path
    }
    if (typeof sessionState.active_table_name === 'string') {
      ingestedTableName.value = sessionState.active_table_name
    }
    if (typeof sessionState.active_conversation_id === 'string') {
      activeConversationId.value = sessionState.active_conversation_id
    }
    if (Array.isArray(sessionState.question_history)) {
      questionHistory.value = sessionState.question_history
        .map((item) => String(item || '').trim())
        .filter((item) => item.length > 0)
        .slice(-MAX_QUESTION_HISTORY)
    }
    if (typeof sessionState.schema_file_id === 'string') {
      schemaFileId.value = sessionState.schema_file_id
    }
    if (typeof sessionState.schema_uploaded === 'boolean') {
      isSchemaFileUploaded.value = sessionState.schema_uploaded
    }

    if (typeof editor.generated_code === 'string') {
      generatedCode.value = editor.generated_code
    }
    if (typeof editor.python_file_content === 'string') {
      pythonFileContent.value = editor.python_file_content
    } else if (typeof editor.generated_code === 'string') {
      pythonFileContent.value = editor.generated_code
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
        schema_context: schemaContext.value,
        allow_schema_sample_values: allowSchemaSampleValues.value,
        allow_llm_data_samples: allowLlmDataSamples.value,
        terminal_risk_acknowledged: terminalConsentGranted.value,
        chat_overlay_width: chatOverlayWidth.value,
        ui_theme: uiTheme.value,
        is_sidebar_collapsed: isSidebarCollapsed.value,
        hide_shortcuts_modal: hideShortcutsModal.value,
        active_workspace_id: activeWorkspaceId.value || '',
        active_dataset_path: dataFilePath.value || '',
        active_table_name: ingestedTableName.value || ''
      })
      applyPreferencesResponse(response, { preserveLocalSchemaContext: true })
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
    dataFilePath.value = ''
    schemaFilePath.value = ''
    schemaFileId.value = ''
    isSchemaFileUploaded.value = false
    ingestedTableName.value = ''
    ingestedColumns.value = []
    columnCatalog.value = []
    profileData.value = null
    schemaContext.value = ''
    allowSchemaSampleValues.value = false
    pythonFileContent.value = ''

    chatHistory.value = []
    questionHistory.value = []
    currentQuestion.value = ''
    currentExplanation.value = ''
    workspaces.value = []
    workspaceDeletionJobs.value = []
    activeWorkspaceId.value = ''
    conversations.value = []
    activeConversationId.value = ''
    turnsNextCursor.value = null
    workspaceKernelStatusById.value = {}

    generatedCode.value = ''
    resultData.value = null
    plotlyFigure.value = null
    dataframes.value = []
    figures.value = []
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
    terminalEnabled.value = false
    runtimeError.value = ''
    terminalConsentGranted.value = false
    terminalCwd.value = ''
    workspaceLayoutMode.value = 'chat'
    historicalCodeBlocks.value = []
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
    kernelEnsureWorkspaceId = ''
    kernelEnsurePromise = null
    ensuredKernelWorkspaceIds.clear()
    workspaceKernelStatusById.value = {}
    clearInMemoryUserState()
  }

  function clearLocalConfig() {
    try {
      clearInMemoryUserState()
      hideShortcutsModal.value = false
      schedulePreferenceSync()
      scheduleLocalSnapshotSave()

      return true
    } catch (error) {
      console.error('Failed to clear local configuration:', error)
      return false
    }
  }

  // Actions
  function setDataFilePath(path) {
    dataFilePath.value = path
    saveLocalConfig()
    if (!path) {
      // Clear chat history when no dataset is selected
      chatHistory.value = []
      generatedCode.value = ''
      pythonFileContent.value = ''
      schemaFileId.value = ''
      isSchemaFileUploaded.value = false
      ingestedTableName.value = ''
      ingestedColumns.value = []
      columnCatalog.value = []
      profileData.value = null
    }
  }

  function setSchemaFilePath(path) {
    schemaFilePath.value = path
    saveLocalConfig()
  }

  function setSchemaFileId(schemaId) {
    schemaFileId.value = schemaId || ''
    saveLocalConfig()
  }

  function setIsSchemaFileUploaded(uploaded) {
    isSchemaFileUploaded.value = !!uploaded
    saveLocalConfig()
  }

  function setIngestedTableName(tableName) {
    ingestedTableName.value = tableName || ''
    saveLocalConfig()
  }

  function setIngestedColumns(columns) {
    ingestedColumns.value = Array.isArray(columns) ? columns : []
    saveLocalConfig()
  }

  function clearActiveDatasetSelection() {
    setDataFilePath('')
    setIngestedColumns([])
    setSchemaFileId('')
    setGeneratedCode('')
    setPythonFileContent('')
    setResultData(null)
    setPlotlyFigure(null)
    setDataframes([])
    setFigures([])
    setTerminalOutput('')
  }

  function handleDatasetRemoved(tableName) {
    const removedTable = String(tableName || '').trim().toLowerCase()
    const activeTable = String(ingestedTableName.value || '').trim().toLowerCase()
    if (!removedTable || !activeTable || removedTable !== activeTable) return false
    clearActiveDatasetSelection()
    return true
  }

  function setColumnCatalog(columns) {
    columnCatalog.value = Array.isArray(columns) ? columns : []
  }

  function setProfileData(data) {
    profileData.value = data && typeof data === 'object' ? data : null
  }

  function setApiKey(key) {
    apiKey.value = key
  }

  function setLlmProvider(provider) {
    const value = String(provider || '').trim().toLowerCase()
    llmProvider.value = value || DEFAULT_PROVIDER
    clearProviderModelSearchState()
    mergeProviderModelOptions(llmProvider.value, [])
    saveLocalConfig()
  }

  function setSelectedLiteModel(model) {
    selectedLiteModel.value = String(model || '').trim()
    saveLocalConfig()
  }

  function setSelectedCodingModel(model) {
    selectedCodingModel.value = String(model || '').trim() || selectedModel.value
    if (selectedCodingModel.value !== selectedModel.value) {
      selectedCodingModel.value = selectedModel.value
    }
    saveLocalConfig()
  }

  function setSlowRequestWarningSeconds(seconds) {
    slowRequestWarningSeconds.value = normalizeSlowRequestWarningSeconds(seconds)
    saveLocalConfig()
  }

  function setProviderDisplayModels(models) {
    const cleaned = normalizeModelList(models, llmProvider.value)
    providerMainModels.value = cleaned.length ? cleaned : [...DEFAULT_MODELS]
    mergeProviderModelOptions(llmProvider.value, [])
    saveLocalConfig()
  }

  // Backward-compatible alias. This mutates provider display cache, not full provider catalog.
  function setEnabledModels(models) {
    setProviderDisplayModels(models)
  }

  function setApiKeyConfigured(configured) {
    apiKeyConfigured.value = !!configured
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

  function setSchemaContext(context) {
    schemaContext.value = context
    saveLocalConfig()
  }

  function setAllowSchemaSampleValues(enabled) {
    allowSchemaSampleValues.value = !!enabled
    saveLocalConfig()
  }

  function setUiTheme(themeId, options = {}) {
    const normalized = normalizeThemeId(themeId)
    if (uiTheme.value === normalized) return
    uiTheme.value = normalized
    if (options?.persist !== false) {
      saveLocalConfig()
    }
  }



  // Python File Management (simplified to single file)
  function setPythonFileContent(content) {
    pythonFileContent.value = content
    saveLocalConfig()
  }

  function createEmptyStreamTrace() {
    return {
      reasoning: [],
      planText: '',
      planNode: '',
      events: [],
      toolCalls: [],
      intervention: null,
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
    if (message.streamTrace.intervention !== null && typeof message.streamTrace.intervention !== 'object') {
      message.streamTrace.intervention = null
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
        intervention: options.streamTrace.intervention && typeof options.streamTrace.intervention === 'object'
          ? options.streamTrace.intervention
          : null,
        stopped: Boolean(options.streamTrace.stopped),
        stoppedReason: String(options.streamTrace.stoppedReason || '')
      }
      : createEmptyStreamTrace()

    // Add to local state
    chatHistory.value.push({
      id: Date.now(),
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
    })
    currentQuestion.value = question
    currentExplanation.value = resultExplanation
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

  function updateLastMessageExplanation(explanation) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    lastMessage.explanation = explanation
    lastMessage.resultExplanation = explanation
    currentExplanation.value = explanation
  }

  function appendLastMessageExplanationChunk(text) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage || typeof text !== 'string' || !text) return
    const current = String(lastMessage.explanation || '')
    const updated = current + text
    lastMessage.explanation = updated
    lastMessage.resultExplanation = updated
    currentExplanation.value = updated
  }

  function setLastMessageCodeExplanation(explanation) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    lastMessage.codeExplanation = String(explanation || '')
  }

  function setLastMessageAnalysisMetadata(metadata) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    const normalized = metadata && typeof metadata === 'object' ? { ...metadata } : {}
    lastMessage.analysisMetadata = normalized
    if (normalized.token_usage && typeof normalized.token_usage === 'object') {
      syncLiveTokenUsageFromChatHistory()
    }
  }

  function toTokenUsageNumber(value) {
    const parsed = Number(value)
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
  }

  function mergeTokenUsageTotals(base, incoming) {
    const left = base && typeof base === 'object' ? base : {}
    const right = incoming && typeof incoming === 'object' ? incoming : {}
    const merged = {
      input_tokens: toTokenUsageNumber(left.input_tokens) + toTokenUsageNumber(right.input_tokens),
      output_tokens: toTokenUsageNumber(left.output_tokens) + toTokenUsageNumber(right.output_tokens),
      cached_tokens: toTokenUsageNumber(left.cached_tokens) + toTokenUsageNumber(right.cached_tokens),
      total_tokens: toTokenUsageNumber(left.total_tokens) + toTokenUsageNumber(right.total_tokens),
      price_usd: toTokenUsageNumber(left.price_usd) + toTokenUsageNumber(right.price_usd),
    }
    if (merged.total_tokens <= 0) {
      merged.total_tokens = merged.input_tokens + merged.output_tokens
    }
    return merged
  }

  function setLiveTokenUsage(usage) {
    if (!usage || typeof usage !== 'object') {
      liveTokenUsage.value = null
      return
    }
    liveTokenUsage.value = { ...usage }
  }

  function setLiveTokenUsageForCurrentTurn(usage) {
    if (!usage || typeof usage !== 'object') return
    const prior = resolveTokenUsageFromChatHistory({ excludeLast: true })
    setLiveTokenUsage(mergeTokenUsageTotals(prior, usage))
  }

  function clearLiveTokenUsage() {
    liveTokenUsage.value = null
  }

  function resolveTokenUsageFromChatHistory(options = {}) {
    const excludeLast = Boolean(options?.excludeLast)
    if (!Array.isArray(chatHistory.value) || chatHistory.value.length === 0) return null
    let totals = null
    const end = excludeLast ? chatHistory.value.length - 1 : chatHistory.value.length
    for (let index = 0; index < end; index += 1) {
      const message = chatHistory.value[index]
      const metadata = message?.analysisMetadata
      const tokenUsage = metadata?.token_usage
      if (tokenUsage && typeof tokenUsage === 'object') {
        totals = mergeTokenUsageTotals(totals, tokenUsage)
      }
    }
    return totals
  }

  function resolveLatestTokenUsageFromChatHistory() {
    return resolveTokenUsageFromChatHistory()
  }

  function syncLiveTokenUsageFromChatHistory() {
    const usage = resolveLatestTokenUsageFromChatHistory()
    if (usage && typeof usage === 'object') {
      setLiveTokenUsage(usage)
      return
    }
    clearLiveTokenUsage()
  }

  function appendLastMessagePlanChunk(text, node = '') {
    const lastMessage = getLastChatMessage()
    if (!lastMessage || typeof text !== 'string' || !text) return
    const trace = ensureMessageStreamTrace(lastMessage)
    if (!trace) return
    trace.planText += text
    if (node) trace.planNode = String(node)
  }

  function appendLastMessageReasoningEvent(event) {
    const lastMessage = getLastChatMessage()
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
  }

  function appendLastMessageTraceEvent(event) {
    const lastMessage = getLastChatMessage()
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
  }

  function markLastMessageStreamStopped(reason = 'Response generation stopped.') {
    const lastMessage = getLastChatMessage()
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
  }

  function appendLastMessageToolCall(event) {
    const lastMessage = getLastChatMessage()
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
  }

  function appendLastMessageToolProgress(event) {
    const lastMessage = getLastChatMessage()
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
  }

  function appendLastMessageToolResult(event) {
    const lastMessage = getLastChatMessage()
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
  }

  function setLastMessageInterventionRequest(event) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage || !event || typeof event !== 'object') return
    const trace = ensureMessageStreamTrace(lastMessage)
    if (!trace) return
    trace.intervention = {
      id: String(event.id || ''),
      prompt: String(event.prompt || ''),
      options: Array.isArray(event.options) ? event.options.map((item) => String(item || '')) : [],
      multi_select: Boolean(event.multi_select),
      timeout_sec: Number.isFinite(Number(event.timeout_sec)) ? Number(event.timeout_sec) : null,
      selected: [],
      status: 'pending',
      requested_at: new Date().toISOString(),
    }
  }

  function setLastMessageInterventionResponse(event) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage || !event || typeof event !== 'object') return
    const trace = ensureMessageStreamTrace(lastMessage)
    if (!trace || !trace.intervention) return
    if (String(event.id || '') !== String(trace.intervention.id || '')) return
    trace.intervention.selected = Array.isArray(event.selected) ? event.selected.map((item) => String(item || '')) : []
    trace.intervention.status = 'submitted'
    trace.intervention.responded_at = new Date().toISOString()
  }

  function markLastMessageInterventionError(interventionId) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    const trace = ensureMessageStreamTrace(lastMessage)
    if (!trace || !trace.intervention) return
    if (String(trace.intervention.id || '') !== String(interventionId || '')) return
    trace.intervention.status = 'error'
  }

  function setLastMessageCodeSnapshot(code) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    const codeSnapshot = String(code || '')
    lastMessage.codeSnapshot = codeSnapshot
    lastMessage.codeUpdated = Boolean(codeSnapshot.trim())
  }

  function setLastMessageTurnId(turnId) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    const normalizedTurnId = String(turnId || '').trim()
    if (!normalizedTurnId) return
    lastMessage.id = normalizedTurnId
  }

  async function fetchChatHistory() {
    try {
      const response = await apiService.getHistory()
      const responseData = response.data || response

      if (responseData) {
        // Backend returns: { messages: [...], current_code: string }
        const messages = responseData.messages || []
        const currentCode = responseData.current_code || ''

        // Update code editor if we have persistent code
        if (currentCode) {
          setGeneratedCode(currentCode)
          setPythonFileContent(currentCode)
        } else {
          setGeneratedCode('')
          setPythonFileContent('')
        }

        // We need to parse the flat list of messages into Q&A pairs
        const history = []
        let currentPair = {}

        messages.forEach((msg, index) => {
          if (msg.role === 'user') {
            if (currentPair.question) {
              history.push({
                ...currentPair,
                id: Date.now() + index,
                streamTrace: null,
                codeSnapshot: '',
                codeUpdated: false,
                toolEvents: null,
                timestamp: new Date().toISOString()
              })
            }
            currentPair = { question: msg.content }
          } else if (msg.role === 'assistant') {
            if (currentPair.question) {
              currentPair.explanation = msg.content
              history.push({
                ...currentPair,
                id: Date.now() + index,
                streamTrace: null,
                codeSnapshot: '',
                codeUpdated: false,
                toolEvents: null,
                timestamp: new Date().toISOString()
              })
              currentPair = {}
            }
          }
        })

        if (currentPair.question) {
          history.push({
            ...currentPair,
            id: Date.now(),
            streamTrace: null,
            codeSnapshot: '',
            codeUpdated: false,
            toolEvents: null,
            timestamp: new Date().toISOString()
          })
        }


        chatHistory.value = history
        syncLiveTokenUsageFromChatHistory()
      } else {
        console.warn("⚠️ fetchChatHistory: No data in response")
        clearLiveTokenUsage()
      }
    } catch (e) {
      console.error("❌ Failed to fetch chat history", e)
      clearLiveTokenUsage()
    }
  }

  function setWorkspaces(items) {
    workspaces.value = Array.isArray(items) ? items : []
    const validWorkspaceIds = new Set(
      workspaces.value
        .map((workspace) => String(workspace?.id || '').trim())
        .filter(Boolean),
    )
    if (validWorkspaceIds.size === 0) {
      workspaceKernelStatusById.value = {}
      ensuredKernelWorkspaceIds.clear()
      return
    }
    const nextStatuses = {}
    Object.entries(workspaceKernelStatusById.value || {}).forEach(([workspaceId, status]) => {
      if (!validWorkspaceIds.has(workspaceId)) {
        ensuredKernelWorkspaceIds.delete(workspaceId)
        return
      }
      nextStatuses[workspaceId] = normalizeKernelStatus(status)
    })
    workspaceKernelStatusById.value = nextStatuses
  }

  function setWorkspaceDeletionJobs(items) {
    workspaceDeletionJobs.value = Array.isArray(items) ? items : []
  }

  function setActiveWorkspaceId(workspaceId) {
    activeWorkspaceId.value = workspaceId || ''
    columnCatalog.value = []
    profileData.value = null
    saveLocalConfig()
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
      const kernelReady = await ensureWorkspaceKernelConnected(workspaceId)
      if (!kernelReady) {
        columnCatalog.value = []
        return []
      }
      const response = await apiService.getWorkspaceColumns(workspaceId)
      const columns = Array.isArray(response?.columns) ? response.columns : []
      columnCatalog.value = columns
      return columns
    } catch (_error) {
      columnCatalog.value = []
      return []
    }
  }

  async function waitForWorkspaceKernelReady(workspaceId, { timeoutMs = 15000, pollMs = 250 } = {}) {
    const targetWorkspaceId = String(workspaceId || '').trim()
    if (!targetWorkspaceId) return false

    const startedAt = Date.now()
    while (Date.now() - startedAt < timeoutMs) {
      try {
        const payload = await apiService.v1GetWorkspaceKernelStatus(targetWorkspaceId)
        const status = normalizeKernelStatus(payload?.status)
        setWorkspaceKernelStatus(targetWorkspaceId, status)
        if (status === 'ready' || status === 'busy') {
          return true
        }
        if (status === 'error') {
          return false
        }
      } catch (_error) {
        // Keep polling while the runtime finishes binding the workspace kernel.
      }

      await new Promise((resolve) => setTimeout(resolve, pollMs))
    }

    return false
  }

  async function ensureWorkspaceKernelConnected(workspaceId = activeWorkspaceId.value) {
    if (!authStore.isAuthenticated) return false
    const targetWorkspaceId = (workspaceId || '').trim()
    if (!targetWorkspaceId) return false
    if (!workspaces.value.some((ws) => ws.id === targetWorkspaceId)) return false

    try {
      const paths = await apiService.v1GetWorkspacePaths(targetWorkspaceId)
      setTerminalEnabled(Boolean(paths?.terminal_enabled))
    } catch (_error) {
      setTerminalEnabled(false)
    }

    const cachedKernelStatus = getWorkspaceKernelStatus(targetWorkspaceId)
    if (cachedKernelStatus === 'ready' || cachedKernelStatus === 'busy') {
      ensuredKernelWorkspaceIds.add(targetWorkspaceId)
      setRuntimeError('')
      return true
    }

    if (kernelEnsurePromise && kernelEnsureWorkspaceId === targetWorkspaceId) {
      return kernelEnsurePromise
    }

    kernelEnsureWorkspaceId = targetWorkspaceId
    kernelEnsurePromise = (async () => {
      try {
        setWorkspaceKernelStatus(targetWorkspaceId, 'starting')
        const bootstrapped = await apiService.v1BootstrapWorkspaceRuntime(targetWorkspaceId)
        if (bootstrapped?.reset === true) {
          setWorkspaceKernelStatus(targetWorkspaceId, 'connecting')
          const kernelReady = await waitForWorkspaceKernelReady(targetWorkspaceId)
          if (kernelReady) {
            setRuntimeError('')
            return true
          }
          setWorkspaceKernelStatus(targetWorkspaceId, 'error')
          setRuntimeError('Workspace runtime is still starting. Wait for Kernel Ready, then try again.')
          setTerminalEnabled(false)
          return false
        }

        setWorkspaceKernelStatus(targetWorkspaceId, 'error')
        setRuntimeError('Workspace runtime bootstrap did not complete.')
        setTerminalEnabled(false)
        return false
      } catch (error) {
        setWorkspaceKernelStatus(targetWorkspaceId, 'error')
        const message = error?.response?.data?.detail || error?.message || 'Workspace runtime bootstrap failed.'
        setRuntimeError(String(message))
        setTerminalEnabled(false)
        return false
      } finally {
        kernelEnsureWorkspaceId = ''
        kernelEnsurePromise = null
      }
    })()

    return kernelEnsurePromise
  }

  function setConversations(items) {
    conversations.value = Array.isArray(items) ? items : []
  }

  function setActiveConversationId(conversationId) {
    activeConversationId.value = conversationId || ''
    activeTurnId.value = ''
    activeTurn.value = null
    activeTurnCode.value = ''
    activeTurnArtifacts.value = []
    activeTurnRelations.value = null
    finalTurnId.value = ''
    turnsNextCursor.value = null
    clearLiveTokenUsage()
    saveLocalConfig()
  }

  function setTurnViewEnabled(enabled) {
    turnViewEnabled.value = Boolean(enabled)
  }

  function setActiveTurnId(turnId) {
    activeTurnId.value = String(turnId || '').trim()
  }

  function setActiveTurnPayload(turn) {
    activeTurn.value = turn && typeof turn === 'object' ? { ...turn } : null
    activeTurnCode.value = String(turn?.code_snapshot || '')
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
    activeTurnArtifacts.value = Array.isArray(payload?.current?.tool_events)
      ? payload.current.tool_events
          .filter((event) => event && event.type === 'artifact' && event.data)
          .map((event) => ({ ...event.data }))
      : []
    hydrateArtifactsFromToolEvents(payload?.current?.tool_events)
  }

  async function loadActiveTurn(turnId = activeTurnId.value) {
    const conversationId = String(activeConversationId.value || '').trim()
    const targetTurnId = String(turnId || '').trim()
    if (!conversationId || !targetTurnId) return null
    const turn = await apiService.v1GetTurn(conversationId, targetTurnId)
    setActiveTurnId(targetTurnId)
    setActiveTurnPayload(turn)
    return turn
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

  async function selectBranchChildTurn(turnId) {
    const targetTurnId = String(turnId || '').trim()
    if (!targetTurnId) return null
    return loadActiveTurnRelations(targetTurnId)
  }

  async function markActiveTurnFinal() {
    return markTurnFinal(activeTurnId.value)
  }

  async function markTurnFinal(turnId) {
    const conversationId = String(activeConversationId.value || '').trim()
    const targetTurnId = String(turnId || '').trim()
    if (!conversationId || !targetTurnId) return null
    const turn = await apiService.v1MarkFinalTurn(conversationId, targetTurnId)
    finalTurnId.value = String(turn?.id || '').trim()
    await loadActiveTurnRelations(targetTurnId)
    return turn
  }

  async function rerunSelectedFinalTurn() {
    const conversationId = String(activeConversationId.value || '').trim()
    if (!conversationId) return null
    const result = await apiService.v1RerunFinalTurn(conversationId)
    const rerunTurnId = String(result?.turn_id || '').trim()
    if (rerunTurnId) {
      await fetchConversationTurns({ reset: true })
      await loadActiveTurnRelations(rerunTurnId)
    }
    return result
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
    const response = await apiService.v1ListWorkspaces()
    const items = response?.workspaces || []
    workspaces.value = items
    await fetchWorkspaceDeletionJobs()
    if (!activeWorkspaceId.value && items.length > 0) {
      const active = items.find((w) => w.is_active) || items[0]
      activeWorkspaceId.value = active.id
      saveLocalConfig()
    }
    if (activeWorkspaceId.value && !items.some((ws) => ws.id === activeWorkspaceId.value)) {
      activeWorkspaceId.value = items[0]?.id || ''
      activeConversationId.value = ''
      chatHistory.value = []
      turnsNextCursor.value = null
      clearLiveTokenUsage()
      if (!activeWorkspaceId.value) {
        setTerminalEnabled(false)
      }
      saveLocalConfig()
    }

    // Workspace-first guard: when user has no workspace, dataset selection must be cleared.
    if (items.length === 0 && (dataFilePath.value || ingestedTableName.value || schemaFileId.value)) {
      dataFilePath.value = ''
      ingestedTableName.value = ''
      ingestedColumns.value = []
      columnCatalog.value = []
      profileData.value = null
      schemaFileId.value = ''
      isSchemaFileUploaded.value = false
      setTerminalEnabled(false)
      saveLocalConfig()
    }

  }

  async function createWorkspace(name) {
    const ws = await apiService.v1CreateWorkspace(name)
    if (ws?.id) {
      await activateWorkspace(ws.id)
    }
    await fetchWorkspaces()
    return ws
  }

  async function activateWorkspace(workspaceId) {
    if (workspaceDeletionJobs.value.some((job) => job.workspace_id === workspaceId)) return
    await apiService.v1ActivateWorkspace(workspaceId)
    activeWorkspaceId.value = workspaceId
    conversations.value = []
    activeConversationId.value = ''
    chatHistory.value = []
    turnsNextCursor.value = null
    clearLiveTokenUsage()
    saveLocalConfig()
  }

  async function renameWorkspace(workspaceId, name) {
    const updated = await apiService.v1RenameWorkspace(workspaceId, name)
    const idx = workspaces.value.findIndex((ws) => ws.id === workspaceId)
    if (idx >= 0) {
      workspaces.value[idx] = { ...workspaces.value[idx], ...updated }
    }
    saveLocalConfig()
    return updated
  }

  async function clearWorkspaceDatabase(workspaceId) {
    const result = await apiService.v1ClearWorkspaceDatabase(workspaceId)
    if (activeWorkspaceId.value === workspaceId) {
      dataFilePath.value = ''
      ingestedTableName.value = ''
      ingestedColumns.value = []
      schemaFileId.value = ''
      isSchemaFileUploaded.value = false
      generatedCode.value = ''
      pythonFileContent.value = ''
      resultData.value = null
      plotlyFigure.value = null
      dataPaneError.value = ''
      setDataframes([])
      setFigures([])
      tablePageOffsets.value = {}
      setSelectedTableArtifact(workspaceId, '')
      setSelectedFigureArtifact(workspaceId, '')
      saveLocalConfig()
    }
    return result
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
    activeConversationId.value = conv.id
    chatHistory.value = []
    turnsNextCursor.value = null
    clearLiveTokenUsage()
    saveLocalConfig()
    return conv
  }

  async function fetchConversationTurns({ reset = true } = {}) {
    if (!activeConversationId.value) return
    const response = await apiService.v1ListTurns(
      activeConversationId.value,
      5,
      reset ? null : turnsNextCursor.value
    )
    const turns = response?.turns || []
    if (reset) {
      chatHistory.value = []
      clearLiveTokenUsage()
    }
    prependChatHistoryFromTurns(turns)
    if (reset) {
      const newestTurnId = String(turns[0]?.id || '').trim()
      if (newestTurnId) {
        setActiveTurnId(newestTurnId)
        await loadActiveTurnRelations(newestTurnId)
      } else {
        setActiveTurnId('')
        setActiveTurnPayload(null)
        setActiveTurnRelations(null)
      }
      await loadFinalTurn(activeConversationId.value)
    }
    if (reset && turns.length === 0) {
      setDataframes([])
      setFigures([])
      clearLiveTokenUsage()
    }
    turnsNextCursor.value = response?.next_cursor || null
  }

  async function clearActiveConversation() {
    if (!activeConversationId.value) return
    await apiService.v1ClearConversation(activeConversationId.value)
    chatHistory.value = []
    turnsNextCursor.value = null
    clearLiveTokenUsage()
  }

  async function deleteConversationById(conversationId) {
    const targetId = String(conversationId || '').trim()
    if (!targetId) return ''

    await apiService.v1DeleteConversation(targetId)
    conversations.value = conversations.value.filter((conversation) => String(conversation?.id || '').trim() !== targetId)

    const currentActiveId = String(activeConversationId.value || '').trim()
    const activeStillExists = currentActiveId
      ? conversations.value.some((conversation) => String(conversation?.id || '').trim() === currentActiveId)
      : false

    if (activeStillExists) return targetId

    const fallbackConversationId = String(conversations.value[0]?.id || '').trim()
    if (currentActiveId !== fallbackConversationId) {
      setActiveConversationId(fallbackConversationId)
    } else {
      saveLocalConfig()
    }

    chatHistory.value = []
    turnsNextCursor.value = null
    clearLiveTokenUsage()

    if (fallbackConversationId) {
      await fetchConversationTurns({ reset: true })
    } else {
      setDataframes([])
      setFigures([])
    }

    return targetId
  }

  async function deleteActiveConversation() {
    if (!activeConversationId.value) return
    await deleteConversationById(activeConversationId.value)
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

  async function fetchWorkspaceDeletionJobs() {
    const response = await apiService.v1ListWorkspaceDeletionJobs()
    workspaceDeletionJobs.value = response?.jobs || []
    workspaceDeletionJobs.value.forEach((job) => {
      if (job?.job_id) {
        pollWorkspaceDeletionJob(job.job_id)
      }
    })
  }

  function upsertWorkspaceDeletionJob(job) {
    const idx = workspaceDeletionJobs.value.findIndex((item) => item.job_id === job.job_id)
    if (idx >= 0) {
      workspaceDeletionJobs.value[idx] = job
    } else {
      workspaceDeletionJobs.value.push(job)
    }
  }

  function removeWorkspaceDeletionJob(jobId) {
    workspaceDeletionJobs.value = workspaceDeletionJobs.value.filter((job) => job.job_id !== jobId)
  }

  async function deleteWorkspaceAsync(workspaceId) {
    const job = await apiService.v1DeleteWorkspace(workspaceId)
    upsertWorkspaceDeletionJob(job)
    setSelectedTableArtifact(workspaceId, '')
    setSelectedFigureArtifact(workspaceId, '')
    if (activeWorkspaceId.value === workspaceId) {
      activeWorkspaceId.value = ''
      activeConversationId.value = ''
      chatHistory.value = []
      turnsNextCursor.value = null
      clearLiveTokenUsage()
      columnCatalog.value = []
      profileData.value = null
      saveLocalConfig()
    }
    pollWorkspaceDeletionJob(job.job_id)
    return job
  }

  const deletionPollers = new Map()

  function pollWorkspaceDeletionJob(jobId, timeoutMs = 300000) {
    if (!jobId || deletionPollers.has(jobId)) return
    const startedAt = Date.now()

    const poll = async () => {
      try {
        const job = await apiService.v1GetWorkspaceDeletionJob(jobId)
        upsertWorkspaceDeletionJob(job)
        if (job.status === 'completed' || job.status === 'failed') {
          deletionPollers.delete(jobId)
          removeWorkspaceDeletionJob(jobId)
          await fetchWorkspaces()
          return
        }

        if (Date.now() - startedAt > timeoutMs) {
          deletionPollers.delete(jobId)
          return
        }

        const timer = setTimeout(poll, 2000)
        deletionPollers.set(jobId, timer)
      } catch (_error) {
        deletionPollers.delete(jobId)
      }
    }

    poll()
  }

  function trackWorkspaceDeletionJob(jobId) {
    pollWorkspaceDeletionJob(jobId)
  }

  function setGeneratedCode(code) {
    generatedCode.value = code
    saveLocalConfig()
  }

  function setResultData(data) {
    resultData.value = data
  }

  function setPlotlyFigure(figure) {
    plotlyFigure.value = figure
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

  function revealArtifactsPane(payload = {}) {
    const hasFigures = Boolean(payload.hasFigures)
    const hasDataframes = Boolean(payload.hasDataframes)
    const hasOutput = Boolean(payload.hasOutput)
    if (!hasFigures && !hasDataframes && !hasOutput) return dataPane.value
    if (workspaceLayoutMode.value === 'chat') {
      workspaceLayoutMode.value = 'split'
    }
    return selectDataPaneForArtifacts({ hasFigures, hasDataframes, hasOutput })
  }

  function setDataframes(dfs) {
    dataframes.value = Array.isArray(dfs) ? dfs : []
  }

  function setFigures(figs) {
    if (!Array.isArray(figs)) {
      figures.value = []
      figureCount.value = 0
      return
    }
    figures.value = figs
      .map((fig, idx) => {
        const normalizedFigure = normalizePlotlyFigure(fig?.data ?? fig)
        if (!normalizedFigure) return null
        const artifactId = String(fig?.artifact_id || normalizedFigure?.artifact_id || '').trim()
        const logicalName = String(fig?.logical_name || normalizedFigure?.logical_name || fig?.name || '').trim()
        return {
          ...(fig || {}),
          name: String(fig?.name || `figure_${idx + 1}`),
          artifact_id: artifactId || undefined,
          logical_name: logicalName || undefined,
          data: normalizedFigure,
        }
      })
      .filter(Boolean)
    figureCount.value = figures.value.length
  }

  function setDataframeCount(count) {
    dataframeCount.value = Number(count || 0)
  }

  function setFigureCount(count) {
    figureCount.value = Number(count || 0)
  }

  function setDataPaneError(msg) {
    dataPaneError.value = String(msg || '')
  }

  function clearDataPaneError() {
    dataPaneError.value = ''
  }

  function setTableViewport(start, end, total) {
    const nextStart = Math.max(0, Number(start || 0))
    const nextEnd = Math.max(0, Number(end || 0))
    const nextTotal = Math.max(0, Number(total || 0))
    if (
      tableWindowStart.value === nextStart &&
      tableWindowEnd.value === nextEnd &&
      tableRowCount.value === nextTotal
    ) {
      return
    }
    tableWindowStart.value = nextStart
    tableWindowEnd.value = nextEnd
    tableRowCount.value = nextTotal
  }

  function clearTableViewport() {
    if (tableWindowStart.value === 0 && tableWindowEnd.value === 0 && tableRowCount.value === 0) {
      return
    }
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    tableRowCount.value = 0
  }

  function tableOffsetKey(workspaceId, artifactId) {
    return `${String(workspaceId || '').trim()}::${String(artifactId || '').trim()}`
  }

  function workspaceSelectionKey(workspaceId) {
    return String(workspaceId || '').trim()
  }

  function setTablePageOffset(workspaceId, artifactId, page) {
    const key = tableOffsetKey(workspaceId, artifactId)
    if (!key || key === '::') return
    const normalizedPage = Math.max(0, Number(page || 0))
    if (Number(tablePageOffsets.value?.[key] || 0) === normalizedPage) return
    tablePageOffsets.value = {
      ...tablePageOffsets.value,
      [key]: normalizedPage
    }
    scheduleLocalSnapshotSave()
  }

  function getTablePageOffset(workspaceId, artifactId) {
    const key = tableOffsetKey(workspaceId, artifactId)
    if (!key || key === '::') return 0
    return Math.max(0, Number(tablePageOffsets.value?.[key] || 0))
  }

  function setSelectedTableArtifact(workspaceId, artifactId) {
    const key = workspaceSelectionKey(workspaceId)
    if (!key) return
    const normalizedArtifactId = String(artifactId || '').trim()
    if (normalizedArtifactId) {
      selectedTableArtifactsByWorkspace.value = {
        ...selectedTableArtifactsByWorkspace.value,
        [key]: normalizedArtifactId
      }
    } else if (Object.prototype.hasOwnProperty.call(selectedTableArtifactsByWorkspace.value, key)) {
      const next = { ...selectedTableArtifactsByWorkspace.value }
      delete next[key]
      selectedTableArtifactsByWorkspace.value = next
    } else {
      return
    }
    scheduleLocalSnapshotSave()
  }

  function getSelectedTableArtifact(workspaceId) {
    const key = workspaceSelectionKey(workspaceId)
    if (!key) return ''
    return String(selectedTableArtifactsByWorkspace.value?.[key] || '').trim()
  }

  function setSelectedFigureArtifact(workspaceId, artifactId) {
    const key = workspaceSelectionKey(workspaceId)
    if (!key) return
    const normalizedArtifactId = String(artifactId || '').trim()
    if (normalizedArtifactId) {
      selectedFigureArtifactsByWorkspace.value = {
        ...selectedFigureArtifactsByWorkspace.value,
        [key]: normalizedArtifactId
      }
    } else if (Object.prototype.hasOwnProperty.call(selectedFigureArtifactsByWorkspace.value, key)) {
      const next = { ...selectedFigureArtifactsByWorkspace.value }
      delete next[key]
      selectedFigureArtifactsByWorkspace.value = next
    } else {
      return
    }
    scheduleLocalSnapshotSave()
  }

  function getSelectedFigureArtifact(workspaceId) {
    const key = workspaceSelectionKey(workspaceId)
    if (!key) return ''
    return String(selectedFigureArtifactsByWorkspace.value?.[key] || '').trim()
  }

  function setTerminalOutput(output) {
    terminalOutput.value = output
  }

  function setTerminalEnabled(enabled) {
    terminalEnabled.value = !!enabled
    if (!terminalEnabled.value && activeTab.value === 'terminal') {
      activeTab.value = 'workspace'
      workspacePane.value = 'code'
    }
  }

  function setRuntimeError(message) {
    runtimeError.value = String(message || '')
  }

  function normalizeKernelStatus(status) {
    const normalized = String(status || '').trim().toLowerCase()
    if (['ready', 'busy', 'starting', 'connecting', 'error', 'missing'].includes(normalized)) {
      return normalized
    }
    return 'missing'
  }

  function setWorkspaceKernelStatus(workspaceId, status) {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return
    const normalizedStatus = normalizeKernelStatus(status)

    const currentStatus = String(workspaceKernelStatusById.value?.[normalizedWorkspaceId] || '').trim()
    if (currentStatus === normalizedStatus) {
      if (normalizedStatus === 'ready' || normalizedStatus === 'busy') {
        ensuredKernelWorkspaceIds.add(normalizedWorkspaceId)
      } else {
        ensuredKernelWorkspaceIds.delete(normalizedWorkspaceId)
      }
      return
    }

    workspaceKernelStatusById.value = {
      ...workspaceKernelStatusById.value,
      [normalizedWorkspaceId]: normalizedStatus
    }

    if (normalizedStatus === 'ready' || normalizedStatus === 'busy') {
      ensuredKernelWorkspaceIds.add(normalizedWorkspaceId)
      if (
        ['ready', 'busy'].includes(normalizedStatus) &&
        normalizedWorkspaceId === String(activeWorkspaceId.value || '').trim()
      ) {
        setRuntimeError('')
      }
      return
    }

    ensuredKernelWorkspaceIds.delete(normalizedWorkspaceId)
  }

  function getWorkspaceKernelStatus(workspaceId = activeWorkspaceId.value) {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return 'missing'
    return normalizeKernelStatus(workspaceKernelStatusById.value?.[normalizedWorkspaceId] || 'missing')
  }

  function clearWorkspaceKernelStatus(workspaceId) {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return
    if (!Object.prototype.hasOwnProperty.call(workspaceKernelStatusById.value, normalizedWorkspaceId)) {
      ensuredKernelWorkspaceIds.delete(normalizedWorkspaceId)
      return
    }
    const nextStatusByWorkspace = { ...workspaceKernelStatusById.value }
    delete nextStatusByWorkspace[normalizedWorkspaceId]
    workspaceKernelStatusById.value = nextStatusByWorkspace
    ensuredKernelWorkspaceIds.delete(normalizedWorkspaceId)
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
    return (
      String(entry.command || '').length +
      String(entry.stdout || '').length +
      String(entry.stderr || '').length +
      String(entry.label || '').length +
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
      label: String(entry.label || (kind === 'output' ? 'Python output' : '')),
      command: String(entry.command || ''),
      stdout,
      stderr,
      exitCode: Number.isInteger(entry.exitCode) ? entry.exitCode : 0,
      runId: String(entry.runId || ''),
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

  function clearTerminalEntries() {
    terminalEntries.value = []
    terminalEntriesTrimmedCount.value = 0
  }

  function setActiveTab(tab) {
    const normalized = String(tab || '').trim().toLowerCase()
    if (normalized === 'code') {
      activeTab.value = 'workspace'
      workspacePane.value = 'code'
    } else if (normalized === 'chat') {
      activeTab.value = 'workspace'
      workspacePane.value = 'chat'
    } else if (['table', 'figure', 'output'].includes(normalized)) {
      // Route data-related tabs to the right pane instead of a full-screen view
      activeTab.value = 'workspace'
      dataPane.value = normalized
    } else if (normalized === 'terminal') {
      // Open the bottom terminal pane instead of navigating away
      activeTab.value = 'workspace'
      isTerminalOpen.value = true
    } else if (normalized === 'preview') {
      activeTab.value = 'workspace'
    } else {
      activeTab.value = normalized || 'workspace'
    }
    saveLocalConfig()
  }
  function setWorkspacePane(pane) {
    workspacePane.value = pane === 'chat' ? 'chat' : 'code'
    activeTab.value = 'workspace'
    saveLocalConfig()
  }
  function setDataPane(pane) {
    const normalizedPane = String(pane || '').trim().toLowerCase()
    dataPane.value = ['table', 'figure', 'output'].includes(normalizedPane) ? normalizedPane : 'table'
    activeTab.value = 'workspace'
    saveLocalConfig()
  }
  function setLeftPaneWidth(widthPct) {
    if (widthPct >= 10 && widthPct <= 90) {
      leftPaneWidth.value = widthPct
      saveLocalConfig()
    }
  }

  function setTerminalHeight(heightPct) {
    if (heightPct >= 10 && heightPct <= 90) {
      terminalHeight.value = heightPct
      saveLocalConfig()
    }
  }

  function toggleTerminal() {
    isTerminalOpen.value = !isTerminalOpen.value
    // If opening the terminal, ensure we are not hiding the workspace if we were previously in a full-screen view.
    if (isTerminalOpen.value && activeTab.value === 'schema-editor') {
      activeTab.value = 'workspace'
    }
    saveLocalConfig()
  }

  function setTerminalConsentGranted(granted) {
    terminalConsentGranted.value = !!granted
    saveLocalConfig()
  }
  function setTerminalCwd(cwd) {
    terminalCwd.value = String(cwd || '')
  }
  function toggleChatOverlay() {
    isChatOverlayOpen.value = !isChatOverlayOpen.value
    saveLocalConfig()
  }
  function setChatOverlayOpen(open) {
    isChatOverlayOpen.value = !!open
    saveLocalConfig()
  }
  function setChatOverlayWidth(widthFraction) {
    if (widthFraction > 0.1 && widthFraction < 0.9) {
      chatOverlayWidth.value = widthFraction
      saveLocalConfig()
    }
  }
  function setSidebarCollapsed(collapsed) {
    isSidebarCollapsed.value = !!collapsed
    saveLocalConfig()
  }
  function setWorkspaceLayoutMode(mode) {
    const normalizedMode = String(mode || '').trim().toLowerCase()
    workspaceLayoutMode.value = ['chat', 'split', 'data'].includes(normalizedMode) ? normalizedMode : 'chat'
    activeTab.value = 'workspace'
    saveLocalConfig()
  }

  function setDataFocusMode(enabled) {
    setWorkspaceLayoutMode(enabled ? 'data' : 'split')
  }

  function toggleDataFocusMode() {
    setDataFocusMode(!isDataFocusMode.value)
  }

  function cycleWorkspaceLayoutMode() {
    const current = String(workspaceLayoutMode.value || 'chat')
    const nextMode = current === 'chat' ? 'split' : current === 'split' ? 'data' : 'chat'
    setWorkspaceLayoutMode(nextMode)
  }
  function setHideShortcutsModal(hide) {
    hideShortcutsModal.value = !!hide
    saveLocalConfig()
  }

  // Editor tracking
  function setEditorPosition(line, col) {
    editorLine.value = line
    editorCol.value = col
  }
  function setEditorFocused(focused) {
    isEditorFocused.value = focused
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  function setCodeRunning(running) {
    isCodeRunning.value = running
  }

  function resetSession() {
    chatHistory.value = []
    liveTokenUsage.value = null
    currentQuestion.value = ''
    currentExplanation.value = ''
    generatedCode.value = ''
    resultData.value = null
    plotlyFigure.value = null
    terminalOutput.value = ''
    terminalEntries.value = []
    terminalEntriesTrimmedCount.value = 0
    terminalEnabled.value = false
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
    workspaceLayoutMode.value = 'chat'
    isTerminalOpen.value = false
    terminalConsentGranted.value = false
    terminalCwd.value = ''
    isCodeRunning.value = false
    schemaFileId.value = ''
    isSchemaFileUploaded.value = false
    columnCatalog.value = []
    profileData.value = null
    historicalCodeBlocks.value = []
    workspaceKernelStatusById.value = {}
    ensuredKernelWorkspaceIds.clear()
    saveLocalConfig()
  }

  function addHistoricalCodeBlock(code) {
    if (code && code.trim()) {
      historicalCodeBlocks.value.push(code)
      saveLocalConfig()
    }
  }

  function applyPreferencesResponse(prefs, options = {}) {
    const preserveLocalSchemaContext = options?.preserveLocalSchemaContext === true
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
    if (!preserveLocalSchemaContext && typeof prefs?.schema_context === 'string') {
      schemaContext.value = prefs.schema_context
    }
    if (typeof prefs?.allow_schema_sample_values === 'boolean') {
      allowSchemaSampleValues.value = prefs.allow_schema_sample_values
    }
    if (typeof prefs?.allow_llm_data_samples === 'boolean') {
      allowLlmDataSamples.value = prefs.allow_llm_data_samples
    }
    if (typeof prefs?.terminal_risk_acknowledged === 'boolean') {
      terminalConsentGranted.value = prefs.terminal_risk_acknowledged
    }
    if (typeof prefs?.plotly_theme_mode === 'string') {
      const normalizedPlotlyThemeMode = prefs.plotly_theme_mode.trim().toLowerCase()
      plotlyThemeMode.value = normalizedPlotlyThemeMode === 'hard' ? 'hard' : 'soft'
    }
    if (typeof prefs?.ui_theme === 'string') {
      uiTheme.value = normalizeThemeId(prefs.ui_theme)
    }
    if (
      typeof prefs?.chat_overlay_width === 'number' &&
      prefs.chat_overlay_width > 0.1 &&
      prefs.chat_overlay_width < 0.9
    ) {
      chatOverlayWidth.value = prefs.chat_overlay_width
    }
    if (typeof prefs?.is_sidebar_collapsed === 'boolean') {
      isSidebarCollapsed.value = prefs.is_sidebar_collapsed
    }
    if (typeof prefs?.hide_shortcuts_modal === 'boolean') {
      hideShortcutsModal.value = prefs.hide_shortcuts_modal
    }
    if (typeof prefs?.api_key_present === 'boolean') {
      apiKeyConfigured.value = prefs.api_key_present
    }
    if (prefs?.active_workspace_id) {
      activeWorkspaceId.value = prefs.active_workspace_id
    }
    if (prefs?.active_dataset_path) {
      dataFilePath.value = prefs.active_dataset_path
    }
    if (prefs?.active_table_name) {
      ingestedTableName.value = prefs.active_table_name
    }

    const providerChanged = previousProvider !== llmProvider.value
    clearProviderModelSearchState()
    if (providerChanged) {
      providerModelSearchQuery.value = ''
    }
    mergeProviderModelOptions(llmProvider.value, [])

    // Preferences may point to deleted/stale workspace IDs.
    if (activeWorkspaceId.value && !workspaces.value.some((ws) => ws.id === activeWorkspaceId.value)) {
      const active = workspaces.value.find((ws) => ws.is_active) || workspaces.value[0]
      activeWorkspaceId.value = active?.id || ''
    }
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
    dataFilePath,
    schemaFilePath,
    schemaFileId,
    isSchemaFileUploaded,
    ingestedTableName,
    ingestedColumns,
    columnCatalog,
    profileData,
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
    schemaContext,
    allowSchemaSampleValues,
    allowLlmDataSamples,
    plotlyThemeMode,
    uiTheme,
    availableThemes,
    pythonFileContent,
    chatHistory,
    questionHistory,
    currentQuestion,
    currentExplanation,
    liveTokenUsage,
    workspaces,
    workspaceDeletionJobs,
    activeWorkspaceId,
    conversations,
    activeConversationId,
    turnViewEnabled,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnArtifacts,
    activeTurnRelations,
    finalTurnId,
    turnsNextCursor,
    workspaceKernelStatusById,
    generatedCode,
    resultData,
    plotlyFigure,
    dataframes,
    figures,
    dataframeCount,
    tableRowCount,
    tableWindowStart,
    tableWindowEnd,
    tablePageOffsets,
    selectedTableArtifactsByWorkspace,
    selectedFigureArtifactsByWorkspace,
    dataPaneError,
    figureCount,
    terminalOutput,
    terminalEntries,
    terminalEntriesTrimmedCount,
    terminalEnabled,
    runtimeError,
    activeTab,
    workspacePane,
    dataPane,
    leftPaneWidth,
    workspaceLayoutMode,
    showLeftPane,
    showRightPane,
    isTerminalOpen,
    terminalHeight,
    terminalConsentGranted,
    terminalCwd,
    isChatOverlayOpen,
    chatOverlayWidth,
    isSidebarCollapsed,
    isDataFocusMode,
    hideShortcutsModal,
    editorLine,
    editorCol,
    isEditorFocused,
    isLoading,
    isCodeRunning,
    historicalCodeBlocks,

    // Computed
    hasDataFile,
    hasSchemaFile,
    canAnalyze,
    hasWorkspace,
    activeWorkspaceKernelStatus,

    // Actions
    saveLocalConfig,
    loadLocalConfig,
    flushLocalConfig,
    clearLocalConfig,
    resetForAuthBoundary,
    setDataFilePath,
    setSchemaFilePath,
    setSchemaFileId,
    setIsSchemaFileUploaded,
    setIngestedTableName,
    setIngestedColumns,
    clearActiveDatasetSelection,
    handleDatasetRemoved,
    setColumnCatalog,
    setProfileData,
    setApiKey,
    setLlmProvider,
    setSelectedLiteModel,
    setSelectedCodingModel,
    setSlowRequestWarningSeconds,
    setProviderDisplayModels,
    setEnabledModels,
    setApiKeyConfigured,
    setSelectedModel,
    searchProviderModels,
    mergeProviderModelOptions,
    clearProviderModelSearchState,
    setSchemaContext,
    setAllowSchemaSampleValues,
    setUiTheme,
    setPythonFileContent,
    addChatMessage,
    addQuestionHistoryEntry,
    updateLastMessageExplanation,
    setLastMessageCodeExplanation,
    setLastMessageAnalysisMetadata,
    setLiveTokenUsage,
    setLiveTokenUsageForCurrentTurn,
    clearLiveTokenUsage,
    syncLiveTokenUsageFromChatHistory,
    appendLastMessageExplanationChunk,
    appendLastMessagePlanChunk,
    appendLastMessageReasoningEvent,
    appendLastMessageTraceEvent,
    appendLastMessageToolCall,
    appendLastMessageToolProgress,
    appendLastMessageToolResult,
    setLastMessageInterventionRequest,
    setLastMessageInterventionResponse,
    markLastMessageInterventionError,
    markLastMessageStreamStopped,
    setLastMessageCodeSnapshot,
    setLastMessageTurnId,
    setWorkspaces,
    setWorkspaceDeletionJobs,
    setActiveWorkspaceId,
    ensureWorkspaceKernelConnected,
    setConversations,
    setActiveConversationId,
    setTurnViewEnabled,
    setActiveTurnId,
    setActiveTurnPayload,
    setActiveTurnRelations,
    loadActiveTurn,
    loadActiveTurnRelations,
    loadFinalTurn,
    goToPreviousTurn,
    goToNextTurn,
    selectBranchChildTurn,
    markActiveTurnFinal,
    markTurnFinal,
    rerunSelectedFinalTurn,
    fetchWorkspaces,
    fetchColumnCatalog,
    fetchWorkspaceDeletionJobs,
    trackWorkspaceDeletionJob,
    createWorkspace,
    deleteWorkspaceAsync,
    activateWorkspace,
    renameWorkspace,
    clearWorkspaceDatabase,
    fetchConversations,
    createConversation,
    fetchConversationTurns,
    clearActiveConversation,
    deleteConversationById,
    deleteActiveConversation,
    updateConversationTitle,
    setGeneratedCode,
    setResultData,
    setPlotlyFigure,
    setDataframes,
    setFigures,
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
    setTerminalEnabled,
    setRuntimeError,
    setWorkspaceKernelStatus,
    getWorkspaceKernelStatus,
    clearWorkspaceKernelStatus,
    appendTerminalEntry,
    updateTerminalEntry,
    clearTerminalEntries,
    setActiveTab,
    setWorkspacePane,
    setDataPane,
    selectDataPaneForArtifacts,
    revealArtifactsPane,
    setLeftPaneWidth,
    setTerminalHeight,
    toggleTerminal,
    setTerminalConsentGranted,
    setTerminalCwd,
    toggleChatOverlay,
    setChatOverlayOpen,
    setChatOverlayWidth,
    setSidebarCollapsed,
    setDataFocusMode,
    toggleDataFocusMode,
    setWorkspaceLayoutMode,
    cycleWorkspaceLayoutMode,
    setHideShortcutsModal,
    setEditorPosition,
    setEditorFocused,
    loadUserPreferences,
    setLoading,
    setCodeRunning,
    resetSession,
    fetchChatHistory,
    addHistoricalCodeBlock
  }
})
