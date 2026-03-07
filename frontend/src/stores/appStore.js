import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { apiService } from '../services/apiService'
import { localStateService } from '../services/localStateService'
import { useAuthStore } from './authStore'
import { normalizePlotlyFigure } from '../utils/figurePayload'

export const useAppStore = defineStore('app', () => {
  const authStore = useAuthStore()
  const DEFAULT_MODELS = [
    'google/gemini-3-flash-preview',
    'google/gemini-2.5-flash',
    'google/gemini-2.5-flash-lite',
    'openrouter/free'
  ]

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
  const selectedModel = ref('google/gemini-2.5-flash')
  const availableModels = ref([...DEFAULT_MODELS])
  const apiKey = ref('')
  const apiKeyConfigured = ref(false)

  // Schema Context
  const schemaContext = ref('')
  const allowSchemaSampleValues = ref(false)
  const plotlyThemeMode = ref('soft')


  // Single Python File per Session (simplified)
  const pythonFileContent = ref('')

  // Chat
  const chatHistory = ref([])
  const currentQuestion = ref('')
  const currentExplanation = ref('')
  const workspaces = ref([])
  const workspaceDeletionJobs = ref([])
  const activeWorkspaceId = ref('')
  const conversations = ref([])
  const activeConversationId = ref('')
  const turnsNextCursor = ref(null)

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
  const workspacePane = ref('code') // 'code' | 'chat'
  const dataPane = ref('table') // 'table' | 'figure' | 'output'
  const leftPaneWidth = ref(50) // percentage
  const terminalConsentGranted = ref(false)
  const isTerminalOpen = ref(false)
  const terminalHeight = ref(30) // percentage
  const terminalCwd = ref('')
  const isChatOverlayOpen = ref(true)
  const chatOverlayWidth = ref(0.25) // 25% of area
  const isSidebarCollapsed = ref(false)
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
  const canAnalyze = computed(() => {
    if (!apiKeyConfigured.value) return false
    return hasWorkspace.value
  })

  let preferenceSyncTimer = null
  let localStateSyncTimer = null
  let suppressPreferenceSync = false
  let kernelEnsureWorkspaceId = ''
  let kernelEnsurePromise = null
  const LOCAL_SNAPSHOT_VERSION = 1
  const MAX_TERMINAL_ENTRIES = 50
  const MAX_TERMINAL_STREAM_CHARS = 200000
  const MAX_TERMINAL_TOTAL_CHARS = 2000000

  function resolveSnapshotUserId(explicitUserId = null) {
    const candidate = String(explicitUserId ?? authStore.userId ?? '').trim()
    return candidate || ''
  }

  function buildLocalStateSnapshot() {
    return {
      version: LOCAL_SNAPSHOT_VERSION,
      updated_at: new Date().toISOString(),
      ui: {
        active_tab: activeTab.value || 'workspace',
        workspace_pane: workspacePane.value || 'code',
        data_pane: dataPane.value || 'table',
        left_pane_width: Number(leftPaneWidth.value || 50),
        chat_overlay_open: !!isChatOverlayOpen.value,
        chat_overlay_width: Number(chatOverlayWidth.value || 0.25),
        terminal_open: !!isTerminalOpen.value,
        terminal_height: Number(terminalHeight.value || 30),
        is_sidebar_collapsed: !!isSidebarCollapsed.value,
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
    const ui = snapshot.ui || {}
    const sessionState = snapshot.session || {}
    const editor = snapshot.editor || {}

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
    if (typeof ui.hide_shortcuts_modal === 'boolean') {
      hideShortcutsModal.value = ui.hide_shortcuts_modal
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
      const activeUserId = resolveSnapshotUserId()
      if (!authStore.isAuthenticated || !activeUserId || activeUserId !== targetUserId) return
      try {
        await apiService.v1UpdatePreferences({
          selected_model: selectedModel.value,
          schema_context: schemaContext.value,
          allow_schema_sample_values: allowSchemaSampleValues.value,
          chat_overlay_width: chatOverlayWidth.value,
          is_sidebar_collapsed: isSidebarCollapsed.value,
          hide_shortcuts_modal: hideShortcutsModal.value,
          active_workspace_id: activeWorkspaceId.value || '',
          active_dataset_path: dataFilePath.value || '',
          active_table_name: ingestedTableName.value || ''
        })
      } catch (_error) {
        // Best-effort sync. Keep UI responsive even if backend is unavailable.
      }
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
    if (localStateSyncTimer) {
      clearTimeout(localStateSyncTimer)
      localStateSyncTimer = null
    }
    await localStateService.saveSnapshot(buildLocalStateSnapshot(), targetUserId)
    return true
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
    selectedModel.value = 'google/gemini-2.5-flash'
    availableModels.value = [...DEFAULT_MODELS]
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
    currentQuestion.value = ''
    currentExplanation.value = ''
    workspaces.value = []
    workspaceDeletionJobs.value = []
    activeWorkspaceId.value = ''
    conversations.value = []
    activeConversationId.value = ''
    turnsNextCursor.value = null

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

  function setColumnCatalog(columns) {
    columnCatalog.value = Array.isArray(columns) ? columns : []
  }

  function setProfileData(data) {
    profileData.value = data && typeof data === 'object' ? data : null
  }

  function setApiKey(key) {
    apiKey.value = key
  }

  function setApiKeyConfigured(configured) {
    apiKeyConfigured.value = !!configured
  }

  function setSelectedModel(model) {
    selectedModel.value = model
    saveLocalConfig()
  }

  function setSchemaContext(context) {
    schemaContext.value = context
    saveLocalConfig()
  }

  function setAllowSchemaSampleValues(enabled) {
    allowSchemaSampleValues.value = !!enabled
    saveLocalConfig()
  }



  // Python File Management (simplified to single file)
  function setPythonFileContent(content) {
    pythonFileContent.value = content
    saveLocalConfig()
  }

  function createEmptyStreamTrace() {
    return {
      planText: '',
      planNode: '',
      events: [],
      toolCalls: [],
      intervention: null
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
    return message.streamTrace
  }

  function addChatMessage(question, explanation, options = {}) {
    const codeSnapshot = String(options?.codeSnapshot || '')
    const streamTrace = options?.streamTrace && typeof options.streamTrace === 'object'
      ? {
          planText: String(options.streamTrace.planText || ''),
          planNode: String(options.streamTrace.planNode || ''),
          events: Array.isArray(options.streamTrace.events) ? options.streamTrace.events : [],
          toolCalls: Array.isArray(options.streamTrace.toolCalls) ? options.streamTrace.toolCalls : [],
          intervention: options.streamTrace.intervention && typeof options.streamTrace.intervention === 'object'
            ? options.streamTrace.intervention
            : null
        }
      : createEmptyStreamTrace()

    // Add to local state
    chatHistory.value.push({
      id: Date.now(),
      question,
      explanation,
      streamTrace,
      codeSnapshot,
      codeUpdated: Boolean(codeSnapshot.trim()),
      toolEvents: Array.isArray(options?.toolEvents) ? options.toolEvents : null,
      timestamp: new Date().toISOString()
    })
    currentQuestion.value = question
    currentExplanation.value = explanation
  }

  function updateLastMessageExplanation(explanation) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage) return
    lastMessage.explanation = explanation
    currentExplanation.value = explanation
  }

  function appendLastMessageExplanationChunk(text) {
    const lastMessage = getLastChatMessage()
    if (!lastMessage || typeof text !== 'string' || !text) return
    const current = String(lastMessage.explanation || '')
    const updated = current + text
    lastMessage.explanation = updated
    currentExplanation.value = updated
  }

  function appendLastMessagePlanChunk(text, node = '') {
    const lastMessage = getLastChatMessage()
    if (!lastMessage || typeof text !== 'string' || !text) return
    const trace = ensureMessageStreamTrace(lastMessage)
    if (!trace) return
    trace.planText += text
    if (node) trace.planNode = String(node)
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
      if (!Array.isArray(existing.lines)) existing.lines = []
      existing.status = String(existing.status || 'running')
      return
    }
    trace.toolCalls.push({
      call_id: callId,
      tool: String(event.tool || ''),
      args: event.args && typeof event.args === 'object' ? event.args : {},
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
      } else {
        console.warn("⚠️ fetchChatHistory: No data in response")
      }
    } catch (e) {
      console.error("❌ Failed to fetch chat history", e)
    }
  }

  function setWorkspaces(items) {
    workspaces.value = Array.isArray(items) ? items : []
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
      const response = await apiService.getWorkspaceColumns(workspaceId)
      const columns = Array.isArray(response?.columns) ? response.columns : []
      columnCatalog.value = columns
      return columns
    } catch (_error) {
      columnCatalog.value = []
      return []
    }
  }

  async function ensureWorkspaceKernelConnected(workspaceId = activeWorkspaceId.value) {
    if (!authStore.isAuthenticated) return false
    const targetWorkspaceId = (workspaceId || '').trim()
    if (!targetWorkspaceId) return false
    if (!workspaces.value.some((ws) => ws.id === targetWorkspaceId)) return false

    if (kernelEnsurePromise && kernelEnsureWorkspaceId === targetWorkspaceId) {
      return kernelEnsurePromise
    }

    kernelEnsureWorkspaceId = targetWorkspaceId
    kernelEnsurePromise = (async () => {
      try {
        const paths = await apiService.v1GetWorkspacePaths(targetWorkspaceId)
        setTerminalEnabled(Boolean(paths?.terminal_enabled))
        const bootstrapped = await apiService.v1BootstrapWorkspaceRuntime(targetWorkspaceId)
        if (bootstrapped?.reset === true) {
          setRuntimeError('')
        }
        return bootstrapped?.reset === true
      } catch (error) {
        const message = error?.response?.data?.detail || error?.message || 'Workspace runtime bootstrap failed.'
        setRuntimeError(String(message))
        setTerminalEnabled(false)
        return false
      } finally {
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
    turnsNextCursor.value = null
    saveLocalConfig()
  }

  function prependChatHistoryFromTurns(turns) {
    if (!Array.isArray(turns) || turns.length === 0) return
    const mapped = turns.map((turn) => ({
      id: turn.id,
      question: turn.user_text,
      explanation: turn.assistant_text,
      toolEvents: turn.tool_events || null,
      streamTrace: null,
      codeSnapshot: turn.code_snapshot || '',
      codeUpdated: Boolean(String(turn.code_snapshot || '').trim()),
      timestamp: turn.created_at || new Date().toISOString()
    }))
    chatHistory.value = [...mapped.reverse(), ...chatHistory.value]
    rehydrateArtifactsFromChatHistory()
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
    if (!activeConversationId.value && conversations.value.length > 0) {
      activeConversationId.value = conversations.value[0].id
    }
  }

  async function createConversation(title = null) {
    if (!activeWorkspaceId.value) return null
    const conv = await apiService.v1CreateConversation(activeWorkspaceId.value, title)
    await fetchConversations()
    activeConversationId.value = conv.id
    chatHistory.value = []
    turnsNextCursor.value = null
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
    }
    prependChatHistoryFromTurns(turns)
    if (reset && turns.length === 0) {
      setDataframes([])
      setFigures([])
    }
    turnsNextCursor.value = response?.next_cursor || null
  }

  async function clearActiveConversation() {
    if (!activeConversationId.value) return
    await apiService.v1ClearConversation(activeConversationId.value)
    chatHistory.value = []
    turnsNextCursor.value = null
  }

  async function deleteActiveConversation() {
    if (!activeConversationId.value) return
    await apiService.v1DeleteConversation(activeConversationId.value)
    const deletedId = activeConversationId.value
    conversations.value = conversations.value.filter((c) => c.id !== deletedId)
    activeConversationId.value = conversations.value[0]?.id || ''
    chatHistory.value = []
    turnsNextCursor.value = null
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
    tableWindowStart.value = Math.max(0, Number(start || 0))
    tableWindowEnd.value = Math.max(0, Number(end || 0))
    tableRowCount.value = Math.max(0, Number(total || 0))
    scheduleLocalSnapshotSave()
  }

  function clearTableViewport() {
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    tableRowCount.value = 0
    scheduleLocalSnapshotSave()
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
    workspacePane.value = 'code'
    dataPane.value = 'table'
    leftPaneWidth.value = 50
    isTerminalOpen.value = false
    terminalConsentGranted.value = false
    terminalCwd.value = ''
    isCodeRunning.value = false
    schemaFileId.value = ''
    isSchemaFileUploaded.value = false
    columnCatalog.value = []
    profileData.value = null
    historicalCodeBlocks.value = []
    saveLocalConfig()
  }

  function addHistoricalCodeBlock(code) {
    if (code && code.trim()) {
      historicalCodeBlocks.value.push(code)
      saveLocalConfig()
    }
  }

  async function loadUserPreferences() {
    try {
      suppressPreferenceSync = true
      const prefs = await apiService.v1GetPreferences()
      if (Array.isArray(prefs?.available_models) && prefs.available_models.length) {
        availableModels.value = prefs.available_models
      }
      if (prefs?.selected_model) selectedModel.value = prefs.selected_model
      if (!availableModels.value.includes(selectedModel.value)) {
        selectedModel.value = availableModels.value[0] || 'google/gemini-2.5-flash'
      }
      if (typeof prefs?.schema_context === 'string') schemaContext.value = prefs.schema_context
      if (typeof prefs?.allow_schema_sample_values === 'boolean') {
        allowSchemaSampleValues.value = prefs.allow_schema_sample_values
      }
      if (typeof prefs?.plotly_theme_mode === 'string') {
        const normalizedPlotlyThemeMode = prefs.plotly_theme_mode.trim().toLowerCase()
        plotlyThemeMode.value = normalizedPlotlyThemeMode === 'hard' ? 'hard' : 'soft'
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

      // Preferences may point to deleted/stale workspace IDs.
      if (activeWorkspaceId.value && !workspaces.value.some((ws) => ws.id === activeWorkspaceId.value)) {
        const active = workspaces.value.find((ws) => ws.is_active) || workspaces.value[0]
        activeWorkspaceId.value = active?.id || ''
      }
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
    selectedModel,
    availableModels,
    apiKey,
    apiKeyConfigured,
    schemaContext,
    allowSchemaSampleValues,
    plotlyThemeMode,
    pythonFileContent,
    chatHistory,
    currentQuestion,
    currentExplanation,
    workspaces,
    workspaceDeletionJobs,
    activeWorkspaceId,
    conversations,
    activeConversationId,
    turnsNextCursor,
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
    isTerminalOpen,
    terminalHeight,
    terminalConsentGranted,
    terminalCwd,
    isChatOverlayOpen,
    chatOverlayWidth,
    isSidebarCollapsed,
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
    setColumnCatalog,
    setProfileData,
    setApiKey,
    setApiKeyConfigured,
    setSelectedModel,
    setSchemaContext,
    setAllowSchemaSampleValues,
    setPythonFileContent,
    addChatMessage,
    updateLastMessageExplanation,
    appendLastMessageExplanationChunk,
    appendLastMessagePlanChunk,
    appendLastMessageTraceEvent,
    appendLastMessageToolCall,
    appendLastMessageToolProgress,
    appendLastMessageToolResult,
    setLastMessageInterventionRequest,
    setLastMessageInterventionResponse,
    markLastMessageInterventionError,
    setLastMessageCodeSnapshot,
    setWorkspaces,
    setWorkspaceDeletionJobs,
    setActiveWorkspaceId,
    ensureWorkspaceKernelConnected,
    setConversations,
    setActiveConversationId,
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
    appendTerminalEntry,
    updateTerminalEntry,
    clearTerminalEntries,
    setActiveTab,
    setWorkspacePane,
    setDataPane,
    setLeftPaneWidth,
    setTerminalHeight,
    toggleTerminal,
    setTerminalConsentGranted,
    setTerminalCwd,
    toggleChatOverlay,
    setChatOverlayOpen,
    setChatOverlayWidth,
    setSidebarCollapsed,
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
