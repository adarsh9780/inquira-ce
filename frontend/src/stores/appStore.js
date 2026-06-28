import { defineStore } from 'pinia'
import { ref, computed, watch, markRaw } from 'vue'
import { apiService } from '../services/apiService'
import { localStateService } from '../services/localStateService'
import { useAuthStore } from './authStore'
import { normalizePlotlyFigure } from '../utils/figurePayload'
import {
  WORKSPACE_LAYOUT_MODES,
  nextWorkspaceLayoutMode,
  normalizeWorkspaceLayoutMode,
  workspaceLayoutVisibility,
} from '../utils/workspaceLayout'
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
  const uiFont = ref(DEFAULT_APP_FONT_ID)
  const availableFonts = APP_FONT_OPTIONS.map((font) => ({ ...font }))
  const uiCodeFont = ref(DEFAULT_CODE_FONT_ID)
  const availableCodeFonts = CODE_FONT_OPTIONS.map((font) => ({ ...font }))


  // Single Python File per Session (simplified)
  const pythonFileContent = ref('')
  const userEditedCode = ref('')
  const hasUserEditedCode = ref(false)
  const codeEditorSource = ref('agent')

  // Chat
  const chatHistory = ref([])
  const questionHistory = ref([])
  const currentQuestion = ref('')
  const currentExplanation = ref('')
  const liveTokenUsage = ref(null)
  const activeConversationUsage = ref(null)
  const conversationUsageById = ref({})
  const workspaces = ref([])
  const workspaceDeletionJobs = ref([])
  const activeWorkspaceId = ref('')
  const conversations = ref([])
  const activeConversationId = ref('')
  const conversationStateById = ref({})
  const conversationRuns = ref({})
  const turnViewEnabled = ref(true)
  const activeTurnId = ref('')
  const activeTurn = ref(null)
  const activeTurnCode = ref('')
  const activeTurnArtifacts = ref([])
  const activeTurnRelations = ref(null)
  const activeTurnTree = ref(null)
  const activeTurnArtifactRefreshKey = ref(0)
  const workspaceTurnTree = ref(null)
  const finalTurnId = ref('')
  const turnsNextCursor = ref(null)
  const workspaceRuntimeStatusById = ref({})

  // Wasm Execution State
  const historicalCodeBlocks = ref([]) // Tracks successfully executed code snippets

  // Analysis
  const generatedCode = ref('')
  const resultData = ref(null)
  const plotlyFigure = ref(null)
  const dataframes = ref([])
  const figures = ref([])
  const scalars = ref([])
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
  const workspaceLayoutMode = ref(WORKSPACE_LAYOUT_MODES.VIEW)
  const hideShortcutsModal = ref(false)
  const isKeyboardShortcutsOpen = ref(false)

  // Editor State
  const editorLine = ref(1)
  const editorCol = ref(1)
  const isEditorFocused = ref(false)

  // UI State
  const isLoading = ref(false)
  const isCodeRunning = ref(false)
  const foregroundOperation = ref(null)
  const backgroundOperations = ref([])

  // Settings trigger
  const isSettingsOpen = ref(false)
  const settingsInitialTab = ref('llm')

  function openSettings(tab = 'llm') {
    const n = String(tab || '').trim().toLowerCase()
    if      (n === 'api'    || n === 'llm')        settingsInitialTab.value = 'llm'
    else if (n === 'workspace' || n === 'data')     settingsInitialTab.value = 'workspace'
    else if (n === 'account')                       settingsInitialTab.value = 'account'
    else if (n === 'appearance' || n === 'theme')   settingsInitialTab.value = 'appearance'
    else if (n === 'terms'  || n === 'legal')       settingsInitialTab.value = 'terms'
    else                                            settingsInitialTab.value = 'llm'

    isSettingsOpen.value = true
  }

  // Computed
  const hasDataFile = computed(() => dataFilePath.value.trim() !== '')
  const hasSchemaFile = computed(() => schemaFilePath.value.trim() !== '' || isSchemaFileUploaded.value)
  const hasWorkspace = computed(() => {
    const activeId = activeWorkspaceId.value.trim()
    if (!activeId) return false
    return workspaces.value.some((ws) => ws.id === activeId)
  })
  const layoutVisibility = computed(() => workspaceLayoutVisibility(workspaceLayoutMode.value))
  const isDataFocusMode = computed(() => workspaceLayoutMode.value === WORKSPACE_LAYOUT_MODES.OUTPUT)
  const showSidebar = computed(() => layoutVisibility.value.showSidebar)
  const showLeftPane = computed(() => layoutVisibility.value.showLeftPane)
  const showRightPane = computed(() => layoutVisibility.value.showRightPane)
  const canAnalyze = computed(() => {
    const hasProviderAccess = providerRequiresApiKey.value
      ? selectedProviderApiKeyPresent.value
      : true
    if (!hasProviderAccess) return false
    return hasWorkspace.value
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
  let runtimeEnsureWorkspaceId = ''
  let runtimeEnsurePromise = null
  let providerModelSearchToken = 0
  const ensuredRuntimeWorkspaceIds = new Set()
  const LOCAL_SNAPSHOT_VERSION = 1
  const MAX_TERMINAL_ENTRIES = 50
  const MAX_TERMINAL_STREAM_CHARS = 200000
  const MAX_TERMINAL_TOTAL_CHARS = 2000000
  const MAX_QUESTION_HISTORY = 30
  const WORKSPACE_PANES = new Set(['code', 'chat', 'ctree'])

  function normalizeWorkspacePane(pane) {
    const normalized = String(pane || '').trim().toLowerCase()
    return WORKSPACE_PANES.has(normalized) ? normalized : 'chat'
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
      currentExplanation: currentExplanation.value,
      activeTurnId: activeTurnId.value,
      activeTurn: cloneConversationValue(activeTurn.value),
      activeTurnCode: activeTurnCode.value,
      activeTurnArtifacts: cloneConversationValue(activeTurnArtifacts.value),
      activeTurnRelations: cloneConversationValue(activeTurnRelations.value),
      activeTurnTree: cloneConversationValue(activeTurnTree.value),
      finalTurnId: finalTurnId.value,
      turnsNextCursor: turnsNextCursor.value,
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
      hasLoadedTurns: existing.hasLoadedTurns === true,
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
      if (Object.prototype.hasOwnProperty.call(statePatch, 'currentExplanation')) currentExplanation.value = String(statePatch.currentExplanation || '')
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
      currentExplanation: '',
      activeTurnId: '',
      activeTurn: null,
      activeTurnCode: '',
      activeTurnArtifacts: [],
      activeTurnRelations: null,
      activeTurnTree: null,
      finalTurnId: '',
      turnsNextCursor: null,
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
      hasLoadedTurns: false,
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
    currentExplanation.value = String(source.currentExplanation || '')
    activeTurnId.value = String(source.activeTurnId || '')
    activeTurn.value = cloneConversationValue(source.activeTurn || null)
    activeTurnCode.value = String(source.activeTurnCode || '')
    activeTurnArtifacts.value = cloneConversationValue(source.activeTurnArtifacts || [])
    activeTurnRelations.value = cloneConversationValue(source.activeTurnRelations || null)
    activeTurnTree.value = cloneConversationValue(source.activeTurnTree || null)
    finalTurnId.value = String(source.finalTurnId || '')
    turnsNextCursor.value = source.turnsNextCursor || null
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
        chat_overlay_open: !!isChatOverlayOpen.value,
        chat_overlay_width: Number(chatOverlayWidth.value || 0.25),
        terminal_open: !!isTerminalOpen.value,
        terminal_height: Number(terminalHeight.value || 30),
        is_sidebar_collapsed: !!isSidebarCollapsed.value,
        workspace_layout_mode: normalizeWorkspaceLayoutMode(workspaceLayoutMode.value),
        data_focus_mode: workspaceLayoutMode.value === WORKSPACE_LAYOUT_MODES.OUTPUT,
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
        active_turn_id: activeTurnId.value || '',
        question_history: Array.isArray(questionHistory.value) ? questionHistory.value : [],
        schema_file_id: schemaFileId.value || '',
        schema_uploaded: !!isSchemaFileUploaded.value,
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
        workspacePane.value = 'ctree'
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
    workspaceLayoutMode.value = normalizeWorkspaceLayoutMode(ui.workspace_layout_mode)
    if (typeof ui.hide_shortcuts_modal === 'boolean') {
      hideShortcutsModal.value = ui.hide_shortcuts_modal
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
    if (typeof sessionState.active_dataset_path === 'string') {
      dataFilePath.value = sessionState.active_dataset_path
    }
    if (typeof sessionState.active_table_name === 'string') {
      ingestedTableName.value = sessionState.active_table_name
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
    if (typeof sessionState.schema_file_id === 'string') {
      schemaFileId.value = sessionState.schema_file_id
    }
    if (typeof sessionState.schema_uploaded === 'boolean') {
      isSchemaFileUploaded.value = sessionState.schema_uploaded
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
    currentExplanation.value = ''
    liveTokenUsage.value = null
    activeConversationUsage.value = null
    conversationUsageById.value = {}
    workspaces.value = []
    workspaceDeletionJobs.value = []
    activeWorkspaceId.value = ''
    conversations.value = []
    activeConversationId.value = ''
    turnsNextCursor.value = null
    workspaceRuntimeStatusById.value = {}

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
    workspaceLayoutMode.value = WORKSPACE_LAYOUT_MODES.VIEW
    foregroundOperation.value = null
    backgroundOperations.value = []
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
    runtimeEnsureWorkspaceId = ''
    runtimeEnsurePromise = null
    ensuredRuntimeWorkspaceIds.clear()
    workspaceRuntimeStatusById.value = {}
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
      userEditedCode.value = ''
      hasUserEditedCode.value = false
      codeEditorSource.value = 'agent'
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

  function setUiFont(fontId, options = {}) {
    const normalized = normalizeAppFontId(fontId)
    if (uiFont.value === normalized) return
    uiFont.value = normalized
    if (options?.persist !== false) {
      saveLocalConfig()
    }
  }

  function setUiCodeFont(fontId, options = {}) {
    const normalized = normalizeCodeFontId(fontId)
    if (uiCodeFont.value === normalized) return
    uiCodeFont.value = normalized
    if (options?.persist !== false) {
      saveLocalConfig()
    }
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
        intervention: options.streamTrace.intervention && typeof options.streamTrace.intervention === 'object'
          ? options.streamTrace.intervention
          : null,
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
        currentExplanation.value = resultExplanation
      } else {
        state.chatHistory = [...(state.chatHistory || []), message]
        state.currentQuestion = question
        state.currentExplanation = resultExplanation
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
    mutateConversationState(targetConversationId, (state, active) => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage) return
      lastMessage.explanation = explanation
      lastMessage.resultExplanation = explanation
      if (active) {
        currentExplanation.value = explanation
      } else {
        state.currentExplanation = explanation
      }
    })
  }

  function appendLastMessageExplanationChunk(text, messageId = null, options = {}) {
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, (state, active) => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || typeof text !== 'string' || !text) return
      const current = String(lastMessage.explanation || '')
      const updated = current + text
      lastMessage.explanation = updated
      lastMessage.resultExplanation = updated
      if (active) {
        currentExplanation.value = updated
      } else {
        state.currentExplanation = updated
      }
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

  function setLastMessageInterventionRequest(event, messageId = null) {
    const options = arguments[2] || {}
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
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
    })
  }

  function setLastMessageInterventionResponse(event, messageId = null) {
    const options = arguments[2] || {}
    const targetConversationId = normalizeConversationId(options?.conversationId || activeConversationId.value)
    mutateConversationState(targetConversationId, () => {
      const lastMessage = getTargetChatMessage(messageId, { conversationId: targetConversationId })
      if (!lastMessage || !event || typeof event !== 'object') return
      const trace = ensureMessageStreamTrace(lastMessage)
      if (!trace || !trace.intervention) return
      if (String(event.id || '') !== String(trace.intervention.id || '')) return
      trace.intervention.selected = Array.isArray(event.selected) ? event.selected.map((item) => String(item || '')) : []
      trace.intervention.status = 'submitted'
      trace.intervention.responded_at = new Date().toISOString()
    })
  }

  function markLastMessageInterventionError(interventionId) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    const trace = ensureMessageStreamTrace(lastMessage)
    if (!trace || !trace.intervention) return
    if (String(trace.intervention.id || '') !== String(interventionId || '')) return
    trace.intervention.status = 'error'
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
      workspaceRuntimeStatusById.value = {}
      ensuredRuntimeWorkspaceIds.clear()
      return
    }
    const nextStatuses = {}
    Object.entries(workspaceRuntimeStatusById.value || {}).forEach(([workspaceId, status]) => {
      if (!validWorkspaceIds.has(workspaceId)) {
        ensuredRuntimeWorkspaceIds.delete(workspaceId)
        return
      }
      nextStatuses[workspaceId] = normalizeWorkspaceRuntimeStatus(status)
    })
    workspaceRuntimeStatusById.value = nextStatuses
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

  async function waitForWorkspaceRuntimeReady(workspaceId, { timeoutMs = 15000, pollMs = 250 } = {}) {
    const targetWorkspaceId = String(workspaceId || '').trim()
    if (!targetWorkspaceId) return false

    const startedAt = Date.now()
    while (Date.now() - startedAt < timeoutMs) {
      try {
        const payload = await apiService.v1GetWorkspaceRuntimeStatus(targetWorkspaceId)
        const status = normalizeWorkspaceRuntimeStatus(payload?.status)
        setWorkspaceRuntimeStatus(targetWorkspaceId, status)
        if (status === 'ready' || status === 'busy') {
          return true
        }
        if (status === 'error') {
          return false
        }
      } catch (_error) {
        // Keep polling while the runtime finishes binding the workspace runtime.
      }

      await new Promise((resolve) => setTimeout(resolve, pollMs))
    }

    return false
  }

  async function ensureWorkspaceRuntimeReady(workspaceId = activeWorkspaceId.value) {
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

    const cachedRuntimeStatus = getWorkspaceRuntimeStatus(targetWorkspaceId)
    if (cachedRuntimeStatus === 'ready' || cachedRuntimeStatus === 'busy') {
      ensuredRuntimeWorkspaceIds.add(targetWorkspaceId)
      setRuntimeError('')
      return true
    }

    if (runtimeEnsurePromise && runtimeEnsureWorkspaceId === targetWorkspaceId) {
      return runtimeEnsurePromise
    }

    runtimeEnsureWorkspaceId = targetWorkspaceId
    runtimeEnsurePromise = (async () => {
      try {
        setWorkspaceRuntimeStatus(targetWorkspaceId, 'starting')
        const bootstrapped = await apiService.v1BootstrapWorkspaceRuntime(targetWorkspaceId)
        if (bootstrapped?.reset === true) {
          setWorkspaceRuntimeStatus(targetWorkspaceId, 'connecting')
          const runtimeReady = await waitForWorkspaceRuntimeReady(targetWorkspaceId)
          if (runtimeReady) {
            setRuntimeError('')
            return true
          }
          setWorkspaceRuntimeStatus(targetWorkspaceId, 'error')
          setRuntimeError('Workspace runtime is still starting. Wait for the workspace to be ready, then try again.')
          setTerminalEnabled(false)
          return false
        }

        setWorkspaceRuntimeStatus(targetWorkspaceId, 'error')
        setRuntimeError('Workspace runtime bootstrap did not complete.')
        setTerminalEnabled(false)
        return false
      } catch (error) {
        setWorkspaceRuntimeStatus(targetWorkspaceId, 'error')
        const message = error?.response?.data?.detail || error?.message || 'Workspace runtime bootstrap failed.'
        setRuntimeError(String(message))
        setTerminalEnabled(false)
        return false
      } finally {
        runtimeEnsureWorkspaceId = ''
        runtimeEnsurePromise = null
      }
    })()

    return runtimeEnsurePromise
  }

  function setConversations(items) {
    conversations.value = Array.isArray(items) ? items : []
  }

  function clearConversationScopedState(options = {}) {
    const preserveChatHistory = Boolean(options?.preserveChatHistory)
    activeTurnId.value = ''
    activeTurn.value = null
    activeTurnCode.value = ''
    activeTurnArtifacts.value = []
    activeTurnRelations.value = null
    activeTurnTree.value = null
    finalTurnId.value = ''
    turnsNextCursor.value = null
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

  function setTurnViewEnabled(enabled) {
    turnViewEnabled.value = Boolean(enabled)
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
    activeTurnArtifacts.value = Array.isArray(payload?.current?.tool_events)
      ? payload.current.tool_events
          .filter((event) => event && event.type === 'artifact' && event.data)
          .map((event) => ({ ...event.data }))
      : []
    hydrateArtifactsFromToolEvents(payload?.current?.tool_events)
    activeTurnArtifactRefreshKey.value += 1
  }

  function refreshActiveTurnArtifacts() {
    activeTurnArtifactRefreshKey.value += 1
  }

  function setActiveTurnTree(payload) {
    activeTurnTree.value = payload && typeof payload === 'object' ? { ...payload } : null
  }

  function setWorkspaceTurnTree(payload) {
    workspaceTurnTree.value = payload && typeof payload === 'object' ? { ...payload } : null
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
    await loadActiveTurnTree(conversationId, targetTurnId)
    return relations
  }

  async function loadActiveTurnTree(
    conversationId = activeConversationId.value,
    currentTurnId = activeTurnId.value,
  ) {
    const targetConversationId = String(conversationId || '').trim()
    if (!targetConversationId) {
      setActiveTurnTree(null)
      return null
    }
    const payload = await apiService.v1GetTurnTree(targetConversationId, currentTurnId)
    setActiveTurnTree(payload)
    return payload
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
    await fetchConversations()
    const isActiveConversation = targetConversationId === String(activeConversationId.value || '').trim()
    const conversationStillExists = conversations.value.some(
      (conversation) => String(conversation?.id || '').trim() === targetConversationId
    )
    if (isActiveConversation && conversationStillExists) {
      await fetchConversationTurns({ reset: true })
    } else if (isActiveConversation) {
      const fallbackConversationId = String(conversations.value[0]?.id || '').trim()
      setActiveConversationId(fallbackConversationId)
      if (fallbackConversationId) {
        await fetchConversationTurns({ reset: true })
      } else {
        clearConversationScopedState()
      }
    } else if (conversationStillExists) {
      await loadActiveTurnTree(targetConversationId, activeTurnId.value)
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

  async function selectBranchChildTurn(turnId) {
    const targetTurnId = String(turnId || '').trim()
    if (!targetTurnId) return null
    return loadActiveTurnRelations(targetTurnId)
  }

  async function markActiveTurnFinal() {
    return markTurnFinal(activeTurnId.value)
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

  async function rerunSelectedFinalTurn() {
    const conversationId = String(activeConversationId.value || '').trim()
    if (!conversationId) return null
    const result = await apiService.v1RerunFinalTurn(conversationId)
    const rerunTurnId = String(result?.turn_id || '').trim()
    if (rerunTurnId) {
      await fetchConversationTurns({ reset: true })
      await loadActiveTurnRelations(rerunTurnId)
      await loadWorkspaceTurnTree()
      await fetchActiveConversationUsage(conversationId)
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

  async function createWorkspace(name, schemaContext = '') {
    const ws = await apiService.v1CreateWorkspace(name, schemaContext)
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
    workspaces.value = workspaces.value.map((workspace) => ({
      ...workspace,
      is_active: workspace.id === workspaceId,
    }))
    conversations.value = []
    activeConversationId.value = ''
    chatHistory.value = []
    turnsNextCursor.value = null
    clearLiveTokenUsage()
    saveLocalConfig()
  }

  async function renameWorkspace(workspaceId, name, schemaContext = undefined) {
    const updated = await apiService.v1RenameWorkspace(workspaceId, name, schemaContext)
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
      userEditedCode.value = ''
      hasUserEditedCode.value = false
      codeEditorSource.value = 'agent'
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

  function dispatchDatasetWorkspaceEvent(name, detail = null) {
    if (typeof window === 'undefined') return
    window.dispatchEvent(new CustomEvent(name, { detail }))
  }

  function applyDatasetSelectionFromIngestionJob(job) {
    const items = Array.isArray(job?.items) ? job.items : []
    const firstCompleted = items.find((item) => String(item?.status || '').toLowerCase() === 'completed')
    if (!firstCompleted) return
    const resolvedPath = String(firstCompleted?.source_path || '').trim()
    const resolvedTableName = String(firstCompleted?.table_name || '').trim()
    if (!resolvedPath && !resolvedTableName) return

    setDataFilePath(resolvedPath)
    setIngestedTableName(resolvedTableName)
    setIngestedColumns([])
    setSchemaFileId(resolvedPath || resolvedTableName)
    dispatchDatasetWorkspaceEvent('dataset-switched', {
      tableName: resolvedTableName || null,
      dataPath: resolvedPath || null,
    })
  }

  async function startDatasetIngestion(paths, options = {}) {
    const workspaceId = String(options?.workspaceId || activeWorkspaceId.value || '').trim()
    const sourcePaths = Array.isArray(paths)
      ? paths.map((item) => String(item || '').trim()).filter(Boolean)
      : []
    if (!workspaceId || sourcePaths.length === 0) return null
    if (workspaceId !== String(activeWorkspaceId.value || '').trim()) {
      throw new Error('Activate the target workspace before importing datasets.')
    }

    const operationId = startBackgroundOperation({
      id: String(options?.operationId || `dataset-ingestion-${Date.now()}`).trim(),
      type: 'dataset-import',
      title: sourcePaths.length === 1 ? 'Importing dataset' : 'Importing datasets',
      message: 'Queueing dataset ingestion...',
      priority: 90,
    })
    const notifyProgress = typeof options?.onProgress === 'function' ? options.onProgress : null
    const notifyComplete = typeof options?.onComplete === 'function' ? options.onComplete : null
    const notifyError = typeof options?.onError === 'function' ? options.onError : null

    try {
      const queued = await apiService.v1AddDatasetsBatch(workspaceId, sourcePaths)
      const jobId = String(queued?.job_id || '').trim()
      if (!jobId) {
        throw new Error('Backend did not return an ingestion job.')
      }
      updateBackgroundOperation(operationId, {
        message: 'Processing 0 of ? datasets',
        progress: null,
      })

      const poll = async () => {
        try {
          const job = await apiService.v1GetDatasetIngestionJob(workspaceId, jobId)
          const status = String(job?.status || '').trim().toLowerCase()
          const completed = Number(job?.completed_count || 0)
          const failed = Number(job?.failed_count || 0)
          const total = Number(job?.total_count || 0)
          const processed = completed + failed
          const progress = total > 0 ? Math.round((processed / total) * 100) : null
          const message = `Processed ${processed} of ${total || '?'} datasets`

          updateBackgroundOperation(operationId, {
            message,
            progress,
          })
          if (notifyProgress) notifyProgress(job)

          if (['completed', 'completed_with_errors', 'failed'].includes(status)) {
            applyDatasetSelectionFromIngestionJob(job)
            dispatchDatasetWorkspaceEvent('dataset-switched', {
              workspaceId,
              source: 'dataset-ingestion',
            })
            await fetchColumnCatalog({ force: true }).catch(() => {})

            const failedCount = Number(job?.failed_count || 0)
            const finalMessage = failedCount > 0
              ? `Completed with ${failedCount} failed import${failedCount === 1 ? '' : 's'}.`
              : 'Import complete.'
            finishBackgroundOperation(operationId, {
              status: status === 'failed' || failedCount > 0 ? 'failed' : 'complete',
              title: failedCount > 0 ? 'Dataset import finished with errors' : 'Dataset import complete',
              message: finalMessage,
            })
            if (notifyComplete) notifyComplete(job)
            return
          }

          setTimeout(poll, 1500)
        } catch (error) {
          const message = String(error?.message || 'Failed to poll dataset ingestion.')
          finishBackgroundOperation(operationId, {
            status: 'failed',
            title: 'Dataset import failed',
            message,
          })
          if (notifyError) notifyError(error)
        }
      }

      setTimeout(poll, 300)
      return { jobId, operationId }
    } catch (error) {
      const message = String(error?.message || 'Failed to queue dataset import.')
      finishBackgroundOperation(operationId, {
        status: 'failed',
        title: 'Dataset import failed',
        message,
      })
      if (notifyError) notifyError(error)
      throw error
    }
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

  async function fetchConversationTurns({ reset = true, preferLatest = false } = {}) {
    const targetConversationId = normalizeConversationId(activeConversationId.value)
    if (!targetConversationId) return
    const cachedState = getConversationState(targetConversationId)
    if (
      reset &&
      isConversationRunning(targetConversationId) &&
      Array.isArray(cachedState?.chatHistory) &&
      cachedState.chatHistory.length > 0
    ) {
      applyConversationStateToActive(targetConversationId, cachedState)
      return
    }
    const preferredTurnId = String(activeTurnId.value || '').trim()
    const response = await apiService.v1ListTurns(
      targetConversationId,
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
      await fetchActiveConversationUsage(targetConversationId)
    }
    if (reset) {
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
    }
    if (reset && turns.length === 0) {
      clearConversationScopedState()
    }
    turnsNextCursor.value = response?.next_cursor || null
    if (reset) {
      syncActiveConversationState({ conversationId: targetConversationId })
      setConversationState(targetConversationId, { hasLoadedTurns: true })
    }
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
      await fetchConversationTurns({ reset: true })
    } else {
      clearConversationScopedState()
    }
    await loadWorkspaceTurnTree()

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
    const jobId = String(job?.job_id || '').trim()
    if (jobId) {
      startBackgroundOperation({
        id: `workspace-deletion-${jobId}`,
        type: 'workspace-delete',
        title: 'Deleting workspace',
        message: 'Workspace cleanup is running...',
        priority: 65,
      })
    }
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
          finishBackgroundOperation(`workspace-deletion-${jobId}`, {
            status: job.status === 'failed' ? 'failed' : 'complete',
            title: job.status === 'failed' ? 'Workspace deletion failed' : 'Workspace deleted',
            message: job.status === 'failed' ? 'Workspace cleanup failed.' : 'Workspace cleanup finished.',
          })
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
    if (workspaceLayoutMode.value === WORKSPACE_LAYOUT_MODES.CHAT) {
      setWorkspaceLayoutMode(WORKSPACE_LAYOUT_MODES.VIEW)
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

  function setScalars(items) {
    scalars.value = Array.isArray(items) ? items : []
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

  function clearWorkspaceRuntimeStatus(workspaceId) {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return
    if (!Object.prototype.hasOwnProperty.call(workspaceRuntimeStatusById.value, normalizedWorkspaceId)) {
      ensuredRuntimeWorkspaceIds.delete(normalizedWorkspaceId)
      return
    }
    const nextStatusByWorkspace = { ...workspaceRuntimeStatusById.value }
    delete nextStatusByWorkspace[normalizedWorkspaceId]
    workspaceRuntimeStatusById.value = nextStatusByWorkspace
    ensuredRuntimeWorkspaceIds.delete(normalizedWorkspaceId)
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
    } else if (normalized === 'ctree') {
      activeTab.value = 'workspace'
      workspacePane.value = 'ctree'
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
    workspacePane.value = normalizeWorkspacePane(pane)
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
    if (isTerminalOpen.value && ['schema-editor', 'conversation-tree'].includes(activeTab.value)) {
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
    const normalizedMode = normalizeWorkspaceLayoutMode(mode)
    workspaceLayoutMode.value = normalizedMode
    if ([WORKSPACE_LAYOUT_MODES.VIEW, WORKSPACE_LAYOUT_MODES.CHAT].includes(normalizedMode)) {
      workspacePane.value = 'chat'
    }
    activeTab.value = 'workspace'
    saveLocalConfig()
  }

  function setDataFocusMode(enabled) {
    setWorkspaceLayoutMode(enabled ? WORKSPACE_LAYOUT_MODES.OUTPUT : WORKSPACE_LAYOUT_MODES.VIEW)
  }

  function toggleDataFocusMode() {
    setDataFocusMode(!isDataFocusMode.value)
  }

  function cycleWorkspaceLayoutMode() {
    setWorkspaceLayoutMode(nextWorkspaceLayoutMode(workspaceLayoutMode.value))
  }

  function setHideShortcutsModal(hide) {
    hideShortcutsModal.value = !!hide
    saveLocalConfig()
  }

  function openKeyboardShortcuts() {
    isKeyboardShortcutsOpen.value = true
  }

  function closeKeyboardShortcuts() {
    isKeyboardShortcutsOpen.value = false
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

  function startForegroundOperation(payload = {}) {
    foregroundOperation.value = normalizeOperationPayload({
      type: 'foreground',
      title: 'Working',
      ...payload,
      status: 'running',
      priority: Number(payload?.priority ?? 100),
    })
    return foregroundOperation.value.id
  }

  function updateForegroundOperation(payload = {}) {
    if (!foregroundOperation.value) return ''
    foregroundOperation.value = {
      ...foregroundOperation.value,
      ...payload,
      progress: Number.isFinite(Number(payload?.progress))
        ? Math.max(0, Math.min(100, Number(payload.progress)))
        : foregroundOperation.value.progress,
      updatedAt: Date.now(),
    }
    return foregroundOperation.value.id
  }

  function clearForegroundOperation(operationId = '') {
    const id = String(operationId || '').trim()
    if (id && String(foregroundOperation.value?.id || '') !== id) return
    foregroundOperation.value = null
  }

  function startBackgroundOperation(payload = {}) {
    const operation = normalizeOperationPayload(payload)
    const existing = backgroundOperations.value.filter((item) => String(item?.id || '') !== operation.id)
    backgroundOperations.value = [...existing, operation]
    return operation.id
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
    const id = String(operationId || '').trim()
    if (!id) return
    updateBackgroundOperation(id, {
      ...payload,
      status: String(payload?.status || 'complete'),
      progress: Number.isFinite(Number(payload?.progress)) ? payload.progress : 100,
    })
    const removeAfterMs = Number(payload?.removeAfterMs ?? 3500)
    if (removeAfterMs >= 0) {
      setTimeout(() => removeBackgroundOperation(id), removeAfterMs)
    }
  }

  function isConversationRunning(conversationId) {
    const id = String(conversationId || '').trim()
    if (!id) return false
    return String(conversationRuns.value?.[id]?.status || '') === 'running'
  }

  function setConversationRun(conversationId, runState = null) {
    const id = String(conversationId || '').trim()
    if (!id) return
    const next = { ...(conversationRuns.value || {}) }
    if (runState && typeof runState === 'object') {
      const current = next[id] || {}
      next[id] = {
        status: String(runState.status || 'running'),
        requestId: String(runState.requestId || current.requestId || ''),
        startedAt: runState.startedAt || current.startedAt || new Date().toISOString(),
        updatedAt: runState.updatedAt || new Date().toISOString(),
        message: String(runState.message || current.message || ''),
        abortController: runState.abortController ? markRaw(runState.abortController) : current.abortController || null,
      }
    } else {
      delete next[id]
    }
    conversationRuns.value = next
  }

  function clearConversationRun(conversationId) {
    setConversationRun(conversationId, null)
  }

  function getConversationRun(conversationId) {
    const id = normalizeConversationId(conversationId)
    return id ? conversationRuns.value?.[id] || null : null
  }

  function abortConversationRun(conversationId) {
    const run = getConversationRun(conversationId)
    const controller = run?.abortController
    if (controller && typeof controller.abort === 'function') {
      controller.abort()
      return true
    }
    return false
  }

  function setCodeRunning(running) {
    isCodeRunning.value = running
    if (running) {
      startBackgroundOperation({
        id: 'code-execution',
        type: 'code',
        title: 'Running code',
        message: 'Executing workspace code...',
        priority: 60,
      })
    } else {
      finishBackgroundOperation('code-execution', {
        title: 'Code run complete',
        message: 'Workspace code execution finished.',
      })
    }
  }

  function resetSession() {
    chatHistory.value = []
    liveTokenUsage.value = null
    activeConversationUsage.value = null
    conversationUsageById.value = {}
    currentQuestion.value = ''
    currentExplanation.value = ''
    generatedCode.value = ''
    pythonFileContent.value = ''
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
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
    workspaceLayoutMode.value = WORKSPACE_LAYOUT_MODES.VIEW
    isTerminalOpen.value = false
    terminalConsentGranted.value = false
    terminalCwd.value = ''
    isCodeRunning.value = false
    foregroundOperation.value = null
    backgroundOperations.value = []
    schemaFileId.value = ''
    isSchemaFileUploaded.value = false
    columnCatalog.value = []
    profileData.value = null
    historicalCodeBlocks.value = []
    workspaceRuntimeStatusById.value = {}
    ensuredRuntimeWorkspaceIds.clear()
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
    if (typeof prefs?.ui_font === 'string') {
      uiFont.value = normalizeAppFontId(prefs.ui_font)
    }
    if (typeof prefs?.ui_code_font === 'string') {
      uiCodeFont.value = normalizeCodeFontId(prefs.ui_code_font)
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
    currentExplanation,
    liveTokenUsage,
    activeConversationUsage,
    conversationUsageById,
    workspaces,
    workspaceDeletionJobs,
    activeWorkspaceId,
    conversations,
    activeConversationId,
    conversationStateById,
    conversationRuns,
    turnViewEnabled,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnArtifacts,
    activeTurnRelations,
    activeTurnTree,
    activeTurnArtifactRefreshKey,
    workspaceTurnTree,
    finalTurnId,
    turnsNextCursor,
    workspaceRuntimeStatusById,
    generatedCode,
    resultData,
    plotlyFigure,
    dataframes,
    figures,
    scalars,
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
    showSidebar,
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
    isKeyboardShortcutsOpen,
    editorLine,
    editorCol,
    isEditorFocused,
    isLoading,
    activeConversationIsLoading,
    runningConversationCount,
    isCodeRunning,
    foregroundOperation,
    backgroundOperations,
    activeBackgroundOperations,
    primaryBackgroundOperation,
    historicalCodeBlocks,

    // Computed
    hasDataFile,
    hasSchemaFile,
    canAnalyze,
    hasWorkspace,
    activeWorkspaceRuntimeStatus,

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
    setLiveTokenUsage,
    setLiveTokenUsageForCurrentTurn,
    clearLiveTokenUsage,
    clearActiveConversationUsage,
    setActiveConversationUsage,
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
    setLastMessageInterventionRequest,
    setLastMessageInterventionResponse,
    markLastMessageInterventionError,
    markLastMessageStreamStopped,
    setLastMessageCodeSnapshot,
    setLastMessageTurnId,
    setWorkspaces,
    setWorkspaceDeletionJobs,
    setActiveWorkspaceId,
    ensureWorkspaceRuntimeReady,
    setConversations,
    setActiveConversationId,
    ensureActiveConversation,
    setTurnViewEnabled,
    setActiveTurnId,
    setActiveTurnPayload,
    setActiveTurnRelations,
    refreshActiveTurnArtifacts,
    setActiveTurnTree,
    loadActiveTurn,
    loadActiveTurnRelations,
    loadActiveTurnTree,
    loadWorkspaceTurnTree,
    deleteTurn,
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
    startDatasetIngestion,
    fetchConversations,
    createConversation,
    fetchConversationTurns,
    deleteConversationById,
    deleteActiveConversation,
    updateConversationTitle,
    setGeneratedCode,
    setResultData,
    setPlotlyFigure,
    setDataframes,
    setFigures,
    setScalars,
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
    setWorkspaceRuntimeStatus,
    getWorkspaceRuntimeStatus,
    clearWorkspaceRuntimeStatus,
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
    openKeyboardShortcuts,
    closeKeyboardShortcuts,
    setEditorPosition,
    setEditorFocused,
    loadUserPreferences,
    setLoading,
    startForegroundOperation,
    updateForegroundOperation,
    clearForegroundOperation,
    startBackgroundOperation,
    updateBackgroundOperation,
    finishBackgroundOperation,
    removeBackgroundOperation,
    isConversationRunning,
    setConversationRun,
    clearConversationRun,
    getConversationRun,
    abortConversationRun,
    setCodeRunning,
    resetSession,
    fetchChatHistory,
    addHistoricalCodeBlock,
    isSettingsOpen,
    settingsInitialTab,
    openSettings
  }
})
