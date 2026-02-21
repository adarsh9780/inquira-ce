<template>
  <div class="space-y-2 sm:space-y-3">
    <!-- Input Area -->
    <div class="relative">
      <textarea
        v-model="question"
        @keydown.enter.prevent="handleSubmit"
        @keydown.shift.enter="handleNewLine"
        placeholder="Ask a question about your data... (Enter to send, Shift+Enter for new line)"
        rows="3"
        class="w-full px-4 sm:px-5 py-2.5 sm:py-3.5 pr-14 sm:pr-18 border border-slate-200 rounded-2xl resize-none focus:outline-none focus:ring-0 focus:border-primary/60 text-sm sm:text-base bg-white shadow-sm transition-all duration-150 leading-relaxed"
        :class="{
          'border-gray-200 bg-gray-50 text-gray-500': !appStore.canAnalyze || appStore.isLoading,
          'hover:shadow': appStore.canAnalyze && !appStore.isLoading
        }"
        :disabled="!appStore.canAnalyze || appStore.isLoading"
      />

      <!-- Send Button -->
      <button
        @click="handleSubmit"
        :disabled="!canSend"
        class="absolute top-1/2 -translate-y-1/2 right-4 sm:right-5 p-2 sm:p-2.5 rounded-lg sm:rounded-xl transition-all duration-200 shadow-sm"
        :class="canSend
          ? 'text-white bg-primary-600 hover:bg-primary-700'
          : 'text-gray-400 bg-gray-100 cursor-not-allowed'
        "
      >
        <PaperAirplaneIcon class="h-4 w-4 sm:h-5 sm:w-5" />
      </button>

    </div>
    
    
    <!-- Requirements Notice -->
    <div v-if="!appStore.canAnalyze" class="bg-error/5 border border-error/20 rounded-xl p-4">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <ExclamationTriangleIcon class="h-5 w-5 text-error" />
        </div>
        <div>
          <h4 class="text-sm font-semibold text-error mb-2">API Key Required</h4>
          <p class="text-sm text-gray-700 mb-3">You need to provide your Gemini API key to start chatting:</p>
          <ul class="space-y-2 text-sm text-gray-700">
            <li class="flex items-center space-x-2">
              <div class="w-1.5 h-1.5 rounded-full bg-error"></div>
              <span>Enter your Gemini API key in Settings</span>
            </li>
          </ul>
          <p class="text-xs text-gray-600 mt-3">Data and schema files are optional - you can chat about general topics without them.</p>
          <p class="text-xs text-gray-600">Click the Settings button in the top toolbar to add your API key.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import pyodideService from '../../services/pyodideService'
import { duckdbService } from '../../services/duckdbService'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { buildBrowserDataPath, hasUsableIngestedColumns, inferTableNameFromDataPath } from '../../utils/chatBootstrap'
import { ensureBrowserTableReady } from '../../utils/browserTableRecovery'
import {
  PaperAirplaneIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const question = ref('')

const canSend = computed(() => {
  return appStore.canAnalyze && 
         question.value.trim().length > 0 && 
         question.value.length <= 1000 &&
         !appStore.isLoading
})

async function buildColumnsWithSamples(tableName, columns) {
  const result = []
  for (const col of columns) {
    const columnName = col?.name
    const columnType = col?.type || col?.dtype || 'VARCHAR'
    if (!columnName) continue

    try {
      const rows = await duckdbService.query(
        `SELECT DISTINCT "${columnName}" AS sample FROM ${tableName} LIMIT 5`
      )
      const samples = rows.map((row) => {
        const value = row.sample
        return typeof value === 'bigint' ? Number(value) : value
      })
      result.push({ name: columnName, dtype: columnType, samples })
    } catch (_err) {
      result.push({ name: columnName, dtype: columnType, samples: [] })
    }
  }
  return result
}

async function ensureBackendSchemaReadyForChat() {
  const tableName = appStore.ingestedTableName
  const backendDataPath = buildBrowserDataPath(tableName)
  if (!backendDataPath) return

  await apiService.setDataPathSimple(backendDataPath)

  if (appStore.schemaContext.trim()) {
    await apiService.setContext(appStore.schemaContext.trim())
  }

  try {
    await apiService.loadSchema(backendDataPath)
    appStore.setIsSchemaFileUploaded(true)
    appStore.setSchemaFileId(backendDataPath)
    return
  } catch (error) {
    if (error.response?.status !== 404) {
      throw error
    }
  }

  if (!hasUsableIngestedColumns(appStore.ingestedColumns)) {
    return
  }

  const columnsWithSamples = await buildColumnsWithSamples(tableName, appStore.ingestedColumns)
  await apiService.generateSchemaFromColumns(
    tableName,
    columnsWithSamples,
    appStore.schemaContext.trim() || null
  )
  appStore.setIsSchemaFileUploaded(true)
  appStore.setSchemaFileId(backendDataPath)
}

async function handleSubmit() {
  if (!canSend.value) return

  const questionText = question.value.trim()
  question.value = ''

  // Add user message immediately to show in chat history
  appStore.addChatMessage(questionText, '')

  // Jump to the code tab so the user can watch generation progress
  appStore.setActiveTab('code')

  appStore.setLoading(true)

  // Create AbortController for cancellation
  const abortController = new AbortController()
  const signal = abortController.signal

  // Timers for timeout handling
  let warningTimer = null
  let cancelTimer = null

  try {
    const expectedTableName = (
      appStore.ingestedTableName ||
      inferTableNameFromDataPath(appStore.dataFilePath)
    ).trim()
    if (expectedTableName && expectedTableName !== appStore.ingestedTableName) {
      appStore.setIngestedTableName(expectedTableName)
      appStore.setSchemaFileId(buildBrowserDataPath(expectedTableName))
    }

    const tableHealth = await ensureBrowserTableReady({
      expectedTableName
    })
    if (tableHealth.recovered) {
      appStore.setIngestedTableName(tableHealth.tableName)
      if (Array.isArray(tableHealth.columns) && tableHealth.columns.length > 0) {
        appStore.setIngestedColumns(tableHealth.columns)
      }
      appStore.setDataFilePath(buildBrowserDataPath(tableHealth.tableName))
      appStore.setSchemaFileId(buildBrowserDataPath(tableHealth.tableName))
    }

    // Get current Python file content if available
    const userCode = appStore.pythonFileContent || null

    // Prepare the request data
    const requestData = {
      current_code: appStore.pythonFileContent || '',
      question: questionText,
      model: appStore.selectedModel,
      context: appStore.schemaContext.trim() || null
    }

    // Log the request for debugging
    console.debug('📤 Sending request to /chat endpoint:', requestData)

    // Keep backend session aligned with browser-native dataset and schema before chat
    await ensureBackendSchemaReadyForChat()

    // Set up timeout timers
    warningTimer = setTimeout(() => {
      toast.warning('Request Taking Longer', 'Your query is taking longer than expected. It will continue processing in the background.')
    }, 30000) // 30 seconds

    cancelTimer = setTimeout(() => {
      toast.error('Request Cancelled', 'Your query took too long and was cancelled. Please try again.')
      abortController.abort()
    }, 300000) // 5 minutes

    let response
    if (appStore.activeWorkspaceId) {
      response = await apiService.v1Analyze({
        workspace_id: appStore.activeWorkspaceId,
        conversation_id: appStore.activeConversationId || null,
        question: questionText,
        current_code: appStore.pythonFileContent || '',
        model: appStore.selectedModel,
        context: appStore.schemaContext.trim() || null
      })
      if (response?.conversation_id && response.conversation_id !== appStore.activeConversationId) {
        appStore.setActiveConversationId(response.conversation_id)
        await appStore.fetchConversations()
      }
    } else {
      try {
        response = await apiService.analyzeDataStream(requestData, {
          signal,
          onEvent: (evt) => {
            if (evt.event === 'status' && evt.data?.message) {
              appStore.updateLastMessageExplanation(evt.data.message)
              return
            }
            if (evt.event === 'node' && evt.data?.node) {
              appStore.updateLastMessageExplanation(`Running: ${evt.data.node}...`)
            }
          }
        })
      } catch (streamError) {
        // Backward-compatible fallback if streaming endpoint is unavailable.
        if (streamError?.status === 404 || streamError?.status === 405) {
          response = await apiService.analyzeData(requestData, signal)
        } else {
          throw streamError
        }
      }
    }

    // Parse the response with new format
    const { is_safe, is_relevant, code, explanation } = response

    // Check if the query is safe and relevant
    if (!is_safe) {
      // Show the rejection reason in the chat window so user understands why
      appStore.updateLastMessageExplanation(explanation || 'Your query was flagged as potentially unsafe.')
      appStore.setActiveTab('code')
      return
    }



    // Update the last message with the explanation
    appStore.updateLastMessageExplanation(explanation)
    appStore.setGeneratedCode(code)

    // Execute the code locally if code was generated
    if (code && code.trim()) {
      try {
        appStore.setTerminalOutput('Executing with Python WebAssembly...\n')
        
        // Execute the code in Pyodide
        const result = await pyodideService.executePython(code)
        
        if (result.success) {
           appStore.addHistoricalCodeBlock(code) // Save it so we can restore on reload
           
           if (result.stdout || result.stderr) {
              appStore.setTerminalOutput(result.stdout + '\n' + result.stderr)
           } else {
              appStore.setTerminalOutput('Execution successful. No terminal output.')
           }
           
           // Based on what type of result Wasm returns, populate the UI
           if (result.resultType === 'dict' && result.result?.data && result.result?.layout) {
              // Plotly figure
              appStore.setPlotlyFigure(result.result)
              appStore.setResultData(null)
              appStore.setActiveTab('chart')
           } else if (result.resultType === 'dict' && result.result?.columns && result.result?.data) {
              // Pandas DataFrame format
              appStore.setResultData(result.result)
              appStore.setPlotlyFigure(null)
              appStore.setActiveTab('table')
           } else {
              // Bare code logic
              appStore.setActiveTab('code')
           }

        } else {
           // Execution failed locally
           appStore.setTerminalOutput('Error executing code:\n' + result.error)
           appStore.setActiveTab('code')
           toast.error('Execution Failed', 'The generated code failed to run locally.')
        }
        
      } catch (err) {
        console.error('Pyodide execution error:', err)
        appStore.setTerminalOutput('Critical error running WebAssembly: ' + err.message)
        appStore.setActiveTab('code')
      }
    } else {
      appStore.setActiveTab('code')
    }

    // Trigger scroll to bottom after message is added
    setTimeout(() => {
      // Find the scrollable container directly
      const scrollableContainer = document.querySelector('[data-chat-scroll-container]')
      if (scrollableContainer) {
        scrollableContainer.scrollTop = scrollableContainer.scrollHeight
      }
    }, 200)



  } catch (error) {
    console.error('Analysis failed:', error)

    // Clear timers
    if (warningTimer) clearTimeout(warningTimer)
    if (cancelTimer) clearTimeout(cancelTimer)

    // Determine error type and show appropriate toast
    let errorTitle = 'Analysis Failed'
    let errorMessage = 'Failed to generate code. Please try again.'

    if (error.name === 'AbortError' || signal.aborted) {
      // Request was cancelled
      errorTitle = 'Request Cancelled'
      errorMessage = 'Your query was cancelled due to timeout.'
    } else if (error.response?.status === 400) {
      errorTitle = 'Invalid Request'
      errorMessage = extractApiErrorMessage(error, 'The request is invalid. Please review your dataset and schema setup.')
    } else if (error.response?.status === 401) {
      errorTitle = 'Authentication Error'
      errorMessage = 'Please check your API key and try again.'
    } else if (error.response?.status === 403) {
      errorTitle = 'Access Denied'
      errorMessage = 'You do not have permission to perform this action.'
    } else if (error.response?.status === 429) {
      errorTitle = 'Rate Limit Exceeded'
      errorMessage = 'Too many requests. Please wait a moment and try again.'
    } else if (error.response?.status >= 500) {
      errorTitle = 'Server Error'
      errorMessage = 'The server encountered an error. Please try again later.'
    } else if (error.code === 'NETWORK_ERROR' || !navigator.onLine) {
      errorTitle = 'Network Error'
      errorMessage = 'Unable to connect to the server. Please check your internet connection.'
    } else if (error.code === 'TIMEOUT' || error.code === 'ECONNABORTED') {
      errorTitle = 'Request Timeout'
      errorMessage = 'The request took too long. Please try again.'
    }

    toast.error(errorTitle, errorMessage)
    appStore.setTerminalOutput(`Error: ${errorMessage}`)
    appStore.updateLastMessageExplanation(errorMessage)

    // Ensure code editor is visible even on error
    appStore.setActiveTab('code')
  } finally {
    // Clear timers
    if (warningTimer) clearTimeout(warningTimer)
    if (cancelTimer) clearTimeout(cancelTimer)

    appStore.setLoading(false)
  }
}

function handleNewLine(event) {
  // Allow Shift+Enter to create new lines
  const textarea = event.target
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  
  question.value = question.value.substring(0, start) + '\n' + question.value.substring(end)
  
  // Move cursor to after the new line
  setTimeout(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  }, 0)
}


</script>
