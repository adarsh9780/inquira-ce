import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { apiService } from '../services/apiService'
import { localStateService } from '../services/localStateService'

export const useAppStore = defineStore('app', () => {

  // Files
  const dataFilePath = ref('')
  const schemaFilePath = ref('')
  const dataFileId = ref('')
  const schemaFileId = ref('')
  const isSchemaFileUploaded = ref(false)
  const ingestedTableName = ref('')
  const ingestedColumns = ref([])

  // LLM Configuration
  const selectedModel = ref('google/gemini-2.5-flash')
  const availableModels = ref([
    'google/gemini-3-flash-preview',
    'google/gemini-2.5-flash',
    'google/gemini-2.5-flash-lite',
    'openrouter/free'
  ])
  const apiKey = ref('')
  const apiKeyConfigured = ref(false)

  // Schema Context
  const schemaContext = ref('')
  const allowSchemaSampleValues = ref(false)


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
  const scalars = ref([])
  const terminalOutput = ref('')
  const activeTab = ref('code')
  const isChatOverlayOpen = ref(true)
  const chatOverlayWidth = ref(0.25) // 25% of area
  const isSidebarCollapsed = ref(true)
  const hideShortcutsModal = ref(false)

  // UI State
  const isLoading = ref(false)
  const isCodeRunning = ref(false)
  const isNotebookMode = ref(false)
  const notebookCells = ref([])
  const activeCellIndex = ref(0)
  const selectedCellIds = ref([])

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
  const LOCAL_SNAPSHOT_VERSION = 1

  function buildLocalStateSnapshot() {
    return {
      version: LOCAL_SNAPSHOT_VERSION,
      updated_at: new Date().toISOString(),
      ui: {
        active_tab: activeTab.value || 'code',
        chat_overlay_open: !!isChatOverlayOpen.value,
        chat_overlay_width: Number(chatOverlayWidth.value || 0.25),
        is_sidebar_collapsed: !!isSidebarCollapsed.value,
        hide_shortcuts_modal: !!hideShortcutsModal.value
      },
      session: {
        active_workspace_id: activeWorkspaceId.value || '',
        active_dataset_path: dataFilePath.value || '',
        active_table_name: ingestedTableName.value || '',
        active_conversation_id: activeConversationId.value || ''
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
      activeTab.value = ui.active_tab
    }
    if (typeof ui.chat_overlay_open === 'boolean') {
      isChatOverlayOpen.value = ui.chat_overlay_open
    }
    if (typeof ui.chat_overlay_width === 'number' && ui.chat_overlay_width > 0.1 && ui.chat_overlay_width < 0.9) {
      chatOverlayWidth.value = ui.chat_overlay_width
    }
    if (typeof ui.is_sidebar_collapsed === 'boolean') {
      isSidebarCollapsed.value = ui.is_sidebar_collapsed
    }
    if (typeof ui.hide_shortcuts_modal === 'boolean') {
      hideShortcutsModal.value = ui.hide_shortcuts_modal
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
    if (preferenceSyncTimer) clearTimeout(preferenceSyncTimer)
    preferenceSyncTimer = setTimeout(async () => {
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
    if (localStateSyncTimer) clearTimeout(localStateSyncTimer)
    localStateSyncTimer = setTimeout(() => {
      void localStateService.saveSnapshot(buildLocalStateSnapshot())
    }, 250)
  }

  async function flushLocalConfig() {
    if (localStateSyncTimer) {
      clearTimeout(localStateSyncTimer)
      localStateSyncTimer = null
    }
    await localStateService.saveSnapshot(buildLocalStateSnapshot())
  }

  async function loadLocalConfig() {
    const snapshot = await localStateService.loadSnapshot()
    if (!snapshot) return false
    return applyLocalStateSnapshot(snapshot)
  }

  function clearLocalConfig() {
    try {
      // Reset all configuration values
      apiKey.value = ''
      apiKeyConfigured.value = false
      selectedModel.value = 'google/gemini-2.5-flash'
      availableModels.value = [
        'google/gemini-3-flash-preview',
        'google/gemini-2.5-flash',
        'google/gemini-2.5-flash-lite',
        'openrouter/free'
      ]
      dataFilePath.value = ''
      schemaFilePath.value = ''
      dataFileId.value = ''
      schemaFileId.value = ''
      isSchemaFileUploaded.value = false
      ingestedTableName.value = ''
      ingestedColumns.value = []
      schemaContext.value = ''
      allowSchemaSampleValues.value = false
      activeWorkspaceId.value = ''
      activeConversationId.value = ''
      historicalCodeBlocks.value = []
      hideShortcutsModal.value = false
      schedulePreferenceSync()

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
      ingestedTableName.value = ''
      ingestedColumns.value = []
    }
  }

  function setSchemaFilePath(path) {
    schemaFilePath.value = path
    saveLocalConfig()
  }

  function setDataFileId(id) {
    dataFileId.value = id
    saveLocalConfig()
  }

  function setSchemaFileId(id) {
    schemaFileId.value = id
    saveLocalConfig()
  }

  function setIsSchemaFileUploaded(uploaded) {
    isSchemaFileUploaded.value = uploaded
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

  function addChatMessage(question, explanation) {
    // Add to local state
    chatHistory.value.push({
      id: Date.now(),
      question,
      explanation,
      timestamp: new Date().toISOString()
    })
    currentQuestion.value = question
    currentExplanation.value = explanation
  }

  function updateLastMessageExplanation(explanation) {
    if (chatHistory.value.length > 0) {
      chatHistory.value[chatHistory.value.length - 1].explanation = explanation
      currentExplanation.value = explanation
    }
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
              history.push({ ...currentPair, id: Date.now() + index, timestamp: new Date().toISOString() })
            }
            currentPair = { question: msg.content }
          } else if (msg.role === 'assistant') {
            if (currentPair.question) {
              currentPair.explanation = msg.content
              history.push({ ...currentPair, id: Date.now() + index, timestamp: new Date().toISOString() })
              currentPair = {}
            }
          }
        })

        if (currentPair.question) {
          history.push({ ...currentPair, id: Date.now(), timestamp: new Date().toISOString() })
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
    saveLocalConfig()
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
      timestamp: turn.created_at || new Date().toISOString()
    }))
    chatHistory.value = [...mapped.reverse(), ...chatHistory.value]
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
      saveLocalConfig()
    }

    // Workspace-first guard: when user has no workspace, dataset selection must be cleared.
    if (items.length === 0 && (dataFilePath.value || ingestedTableName.value || schemaFileId.value)) {
      dataFilePath.value = ''
      ingestedTableName.value = ''
      ingestedColumns.value = []
      schemaFileId.value = ''
      isSchemaFileUploaded.value = false
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
    if (activeWorkspaceId.value === workspaceId) {
      activeWorkspaceId.value = ''
      activeConversationId.value = ''
      chatHistory.value = []
      turnsNextCursor.value = null
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
    figures.value = Array.isArray(figs) ? figs : []
  }

  function setScalars(scs) {
    scalars.value = Array.isArray(scs) ? scs : []
  }

  function setTerminalOutput(output) {
    terminalOutput.value = output
  }

  function setActiveTab(tab) {
    activeTab.value = tab
    saveLocalConfig()
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
    isSidebarCollapsed.value = collapsed
    saveLocalConfig()
  }

  function setHideShortcutsModal(hidden) {
    hideShortcutsModal.value = !!hidden
    saveLocalConfig()
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  function setCodeRunning(running) {
    isCodeRunning.value = running
  }

  function setNotebookMode(mode) {
    isNotebookMode.value = mode
  }

  function setNotebookCells(cells) {
    notebookCells.value = Array.isArray(cells) ? cells : []
  }

  function addNotebookCell(cell, index = null) {
    const newCell = {
      id: Date.now() + Math.random(), // Use timestamp + random for unique ID
      content: cell.content || '',
      output: cell.output || '',
      isRunning: false,
      ...cell
    }

    if (index === null || index >= notebookCells.value.length) {
      notebookCells.value.push(newCell)
    } else {
      notebookCells.value.splice(index, 0, newCell)
    }
  }

  function updateNotebookCell(id, updates) {
    const cellIndex = notebookCells.value.findIndex(cell => cell.id === id)
    if (cellIndex !== -1) {
      notebookCells.value[cellIndex] = { ...notebookCells.value[cellIndex], ...updates }
    }
  }

  function deleteNotebookCell(id) {
    const cellIndex = notebookCells.value.findIndex(cell => cell.id === id)
    if (cellIndex !== -1) {
      notebookCells.value.splice(cellIndex, 1)
    }
  }

  function clearNotebookCells() {
    notebookCells.value = []
  }

  function setActiveCellIndex(index) {
    activeCellIndex.value = index
  }

  function setSelectedCellIds(ids) {
    selectedCellIds.value = Array.isArray(ids) ? ids : []
  }

  function toggleCellSelection(cellId) {
    const index = selectedCellIds.value.indexOf(cellId)
    if (index > -1) {
      selectedCellIds.value.splice(index, 1)
    } else {
      selectedCellIds.value.push(cellId)
    }
  }

  function clearCellSelection() {
    selectedCellIds.value = []
  }

  function resetSession() {
    chatHistory.value = []
    currentQuestion.value = ''
    currentExplanation.value = ''
    generatedCode.value = ''
    resultData.value = null
    plotlyFigure.value = null
    terminalOutput.value = ''
    activeTab.value = 'code'
    isCodeRunning.value = false
    isNotebookMode.value = false
    notebookCells.value = []
    activeCellIndex.value = 0
    selectedCellIds.value = []
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
    dataFileId,
    schemaFileId,
    isSchemaFileUploaded,
    ingestedTableName,
    ingestedColumns,
    selectedModel,
    availableModels,
    apiKey,
    apiKeyConfigured,
    schemaContext,
    allowSchemaSampleValues,
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
    scalars,
    terminalOutput,
    activeTab,
    isChatOverlayOpen,
    chatOverlayWidth,
    isSidebarCollapsed,
    hideShortcutsModal,
    isLoading,
    isCodeRunning,
    isNotebookMode,
    notebookCells,
    activeCellIndex,
    selectedCellIds,
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
    setDataFilePath,
    setSchemaFilePath,
    setDataFileId,
    setSchemaFileId,
    setIsSchemaFileUploaded,
    setIngestedTableName,
    setIngestedColumns,
    setApiKey,
    setApiKeyConfigured,
    setSelectedModel,
    setSchemaContext,
    setAllowSchemaSampleValues,
    setPythonFileContent,
    addChatMessage,
    updateLastMessageExplanation,
    setWorkspaces,
    setWorkspaceDeletionJobs,
    setActiveWorkspaceId,
    setConversations,
    setActiveConversationId,
    fetchWorkspaces,
    fetchWorkspaceDeletionJobs,
    trackWorkspaceDeletionJob,
    createWorkspace,
    deleteWorkspaceAsync,
    activateWorkspace,
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
    setScalars,
    setTerminalOutput,
    setActiveTab,
    toggleChatOverlay,
    setChatOverlayOpen,
    setChatOverlayWidth,
    setSidebarCollapsed,
    setHideShortcutsModal,
    loadUserPreferences,
    setLoading,
    setCodeRunning,
    setNotebookMode,
    setNotebookCells,
    addNotebookCell,
    updateNotebookCell,
    deleteNotebookCell,
    clearNotebookCells,
    setActiveCellIndex,
    setSelectedCellIds,
    toggleCellSelection,
    clearCellSelection,
    resetSession,
    fetchChatHistory,
    addHistoricalCodeBlock
  }
})
