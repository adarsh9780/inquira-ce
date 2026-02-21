import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { apiService } from '../services/apiService'

// Local storage keys
const STORAGE_KEYS = {
  CONFIG: 'llm-analysis-config',
  SESSION: 'llm-analysis-session-id'
}

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
  const selectedModel = ref('gemini-2.5-flash')
  const apiKey = ref('')

  // Schema Context
  const schemaContext = ref('')


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
  const canAnalyze = computed(() => {
    if (apiKey.value.trim() === '') return false
    return activeWorkspaceId.value.trim() !== ''
  })
  const hasWorkspace = computed(() => activeWorkspaceId.value.trim() !== '')

  // Local Configuration Management
  function saveLocalConfig() {
    const config = {
      apiKey: apiKey.value,
      selectedModel: selectedModel.value,
      dataFilePath: dataFilePath.value,
      schemaFilePath: schemaFilePath.value,
      dataFileId: dataFileId.value,
      schemaFileId: schemaFileId.value,
      isSchemaFileUploaded: isSchemaFileUploaded.value,
      ingestedTableName: ingestedTableName.value,
      ingestedColumns: ingestedColumns.value,
      schemaContext: schemaContext.value,
      activeWorkspaceId: activeWorkspaceId.value,
      activeConversationId: activeConversationId.value,
      chatOverlayWidth: chatOverlayWidth.value,
      historicalCodeBlocks: historicalCodeBlocks.value,
      timestamp: new Date().toISOString()
    }

    try {
      localStorage.setItem(STORAGE_KEYS.CONFIG, JSON.stringify(config))
    } catch (error) {
      console.error('❌ Failed to save configuration:', error)
    }
  }

  function loadLocalConfig() {
    try {
      const configStr = localStorage.getItem(STORAGE_KEYS.CONFIG)
      if (!configStr) {
        return false
      }

      const config = JSON.parse(configStr)

      // Restore API key and model
      if (config.apiKey) {
        apiKey.value = config.apiKey
      }
      if (config.selectedModel) {
        selectedModel.value = config.selectedModel
      }

      // Restore data file path
      if (config.dataFilePath) {
        dataFilePath.value = config.dataFilePath
      }

      // Restore schema file path
      if (config.schemaFilePath) {
        schemaFilePath.value = config.schemaFilePath
      }

      // Restore file IDs
      if (config.dataFileId) {
        dataFileId.value = config.dataFileId
      }
      if (config.schemaFileId) {
        schemaFileId.value = config.schemaFileId
      }

      // Restore schema upload status
      if (config.isSchemaFileUploaded !== undefined) {
        isSchemaFileUploaded.value = config.isSchemaFileUploaded
      }
      if (config.ingestedTableName) {
        ingestedTableName.value = config.ingestedTableName
      }
      if (Array.isArray(config.ingestedColumns)) {
        ingestedColumns.value = config.ingestedColumns
      }

      // Restore schema context
      if (config.schemaContext) {
        schemaContext.value = config.schemaContext
      }
      if (config.activeWorkspaceId) {
        activeWorkspaceId.value = config.activeWorkspaceId
      }
      if (config.activeConversationId) {
        activeConversationId.value = config.activeConversationId
      }

      // Restore chat overlay width
      if (config.chatOverlayWidth && config.chatOverlayWidth > 0.1 && config.chatOverlayWidth < 0.9) {
        chatOverlayWidth.value = config.chatOverlayWidth
      }

      // Restore historical code blocks for Pyodide
      if (config.historicalCodeBlocks) {
        historicalCodeBlocks.value = config.historicalCodeBlocks
      }
      return true
    } catch (error) {
      console.error('Failed to load local configuration:', error)
      // Clear corrupted config
      localStorage.removeItem(STORAGE_KEYS.CONFIG)
      return false
    }
  }

  function clearLocalConfig() {
    try {
      localStorage.removeItem(STORAGE_KEYS.CONFIG)

      // Reset all configuration values
      apiKey.value = ''
      selectedModel.value = 'gemini-2.5-flash'
      dataFilePath.value = ''
      schemaFilePath.value = ''
      dataFileId.value = ''
      schemaFileId.value = ''
      isSchemaFileUploaded.value = false
      ingestedTableName.value = ''
      ingestedColumns.value = []
      schemaContext.value = ''
      activeWorkspaceId.value = ''
      activeConversationId.value = ''
      historicalCodeBlocks.value = []

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
    saveLocalConfig()
  }

  function setSelectedModel(model) {
    selectedModel.value = model
    saveLocalConfig()
  }

  function setSchemaContext(context) {
    schemaContext.value = context
    saveLocalConfig()
  }



  // Python File Management (simplified to single file)
  function setPythonFileContent(content) {
    pythonFileContent.value = content
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
  }
  function toggleChatOverlay() {
    isChatOverlayOpen.value = !isChatOverlayOpen.value
  }
  function setChatOverlayOpen(open) {
    isChatOverlayOpen.value = !!open
  }
  function setChatOverlayWidth(widthFraction) {
    if (widthFraction > 0.1 && widthFraction < 0.9) {
      chatOverlayWidth.value = widthFraction
      saveLocalConfig()
    }
  }
  function setSidebarCollapsed(collapsed) {
    isSidebarCollapsed.value = collapsed
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
    apiKey,
    schemaContext,
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
    clearLocalConfig,
    setDataFilePath,
    setSchemaFilePath,
    setDataFileId,
    setSchemaFileId,
    setIsSchemaFileUploaded,
    setIngestedTableName,
    setIngestedColumns,
    setApiKey,
    setSelectedModel,
    setSchemaContext,
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
