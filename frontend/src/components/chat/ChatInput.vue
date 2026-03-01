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
        class="absolute bottom-3 right-3 p-2.5 rounded-xl transition-all duration-200 shadow-sm z-40 flex-shrink-0"
        :class="canSend
          ? 'text-white bg-primary-600 hover:bg-primary-700 hover:scale-105 active:scale-95'
          : 'text-gray-400 bg-gray-200 cursor-not-allowed'
        "
        :title="canSend ? 'Send question' : 'Fill requirements to enable send'"
      >
        <PaperAirplaneIcon class="h-5 w-5" />
      </button>

    </div>
    
    
    <!-- Requirements Notice -->
    <div v-if="!appStore.canAnalyze" class="bg-error/5 border border-error/20 rounded-xl p-4">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <ExclamationTriangleIcon class="h-5 w-5 text-error" />
        </div>
        <div>
          <h4 class="text-sm font-semibold text-error mb-2">Setup Required</h4>
          <p class="text-sm text-gray-700 mb-3">Before chatting, complete this setup:</p>
          <ul class="space-y-2 text-sm text-gray-700">
            <li class="flex items-center space-x-2">
              <div class="w-1.5 h-1.5 rounded-full bg-error"></div>
              <span>Create or select a workspace from the header dropdown</span>
            </li>
            <li class="flex items-center space-x-2">
              <div class="w-1.5 h-1.5 rounded-full bg-error"></div>
              <span>Enter your OpenRouter API key in Settings</span>
            </li>
          </ul>
          <p class="text-xs text-gray-600 mt-3">Click the Settings button in the top toolbar to add your API key.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { buildBrowserDataPath, inferTableNameFromDataPath } from '../../utils/chatBootstrap'
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

function isBrowserVirtualPath(path) {
  const normalized = String(path || '').toLowerCase()
  return normalized.startsWith('browser://') || normalized.startsWith('browser:/') || normalized.startsWith('/browser:/')
}

function isRecoverableBrowserTableError(error) {
  const message = String(error?.message || '')
  return (
    message.includes('Dataset is not loaded in this browser session') ||
    message.includes('No saved data file handle found') ||
    message.includes('Saved file reference is stale') ||
    message.includes('Data file permission was not granted') ||
    message.includes('Dataset could not be loaded in this browser session')
  )
}

async function ensureWorkspaceDatasetReady(workspaceId) {
  if (!workspaceId || !appStore.dataFilePath) return
  const tableName = (
    appStore.ingestedTableName ||
    inferTableNameFromDataPath(appStore.dataFilePath)
  ).trim()
  if (!tableName) {
    throw new Error('Dataset sync failed: missing selected table name.')
  }

  if (isBrowserVirtualPath(appStore.dataFilePath)) {
    const columns = (Array.isArray(appStore.ingestedColumns) ? appStore.ingestedColumns : []).map((col) => ({
      ...col,
      samples: appStore.allowSchemaSampleValues && Array.isArray(col?.samples) ? col.samples : []
    }))
    await apiService.v1SyncBrowserDataset(workspaceId, {
      table_name: tableName,
      columns,
      row_count: null,
      allow_sample_values: appStore.allowSchemaSampleValues
    })
    return
  }

  try {
    await apiService.v1AddDataset(workspaceId, appStore.dataFilePath)
    return
  } catch (_error) {
    throw new Error('Dataset sync failed: selected file could not be attached to workspace.')
  }
}

function buildActiveSchemaPayload() {
  const tableName = (
    appStore.ingestedTableName ||
    inferTableNameFromDataPath(appStore.dataFilePath)
  ).trim()

  if (!tableName) return { tableName: null, activeSchema: null }

  const columns = (Array.isArray(appStore.ingestedColumns) ? appStore.ingestedColumns : [])
    .filter((col) => col?.name)
    .map((col) => ({
      name: col.name,
      dtype: col.type || col.dtype || 'VARCHAR',
      description: col.description || '',
      samples: appStore.allowSchemaSampleValues && Array.isArray(col.samples) ? col.samples : []
    }))

  return {
    tableName,
    activeSchema: {
      table_name: tableName,
      columns
    }
  }
}

async function handleSubmit() {
  if (!canSend.value) return

  const questionText = question.value.trim()
  question.value = ''

  // Add user message immediately to show in chat history
  appStore.addChatMessage(questionText, '')

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
    }

    const workspaceId = appStore.activeWorkspaceId
    if (!workspaceId) {
      throw new Error('Create/select a workspace before analysis.')
    }

    // Sync dataset metadata only when a dataset is selected.
    await ensureWorkspaceDatasetReady(workspaceId)

    // Set up timeout timers
    warningTimer = setTimeout(() => {
      toast.warning('Request Taking Longer', 'Your query is taking longer than expected. It will continue processing in the background.')
    }, 30000) // 30 seconds

    cancelTimer = setTimeout(() => {
      toast.error('Request Cancelled', 'Your query took too long and was cancelled. Please try again.')
      abortController.abort()
    }, 300000) // 5 minutes

    let response
    const schemaPayload = buildActiveSchemaPayload()
    try {
      response = await apiService.v1AnalyzeStream(
        {
          workspace_id: workspaceId,
          conversation_id: appStore.activeConversationId || null,
          question: questionText,
          current_code: appStore.pythonFileContent || '',
          model: appStore.selectedModel,
          context: appStore.schemaContext.trim() || null,
          table_name: schemaPayload.tableName,
          active_schema: schemaPayload.activeSchema,
          api_key: null
        },
        {
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
        }
      )
    } catch (streamError) {
      // Fallback if streaming fails or is unsupported
      if (streamError?.status === 404 || streamError?.status === 405) {
        response = await apiService.v1Analyze({
          workspace_id: workspaceId,
          conversation_id: appStore.activeConversationId || null,
          question: questionText,
          current_code: appStore.pythonFileContent || '',
          model: appStore.selectedModel,
          context: appStore.schemaContext.trim() || null,
          table_name: schemaPayload.tableName,
          active_schema: schemaPayload.activeSchema,
          api_key: null
        })
      } else {
        throw streamError
      }
    }

    if (response?.conversation_id && response.conversation_id !== appStore.activeConversationId) {
      appStore.setActiveConversationId(response.conversation_id)
      await appStore.fetchConversations()
    }

    // Parse the response with new format
    const { is_safe, is_relevant, code, current_code, explanation } = response
    const finalCode = (code ?? current_code ?? '').toString()

    // Check if the query is safe and relevant
    if (!is_safe) {
      // Show the rejection reason in the chat window so user understands why
      appStore.updateLastMessageExplanation(explanation || 'Your query was flagged as potentially unsafe.')
      return
    }



    // Update the last message with the explanation
    appStore.updateLastMessageExplanation(explanation)
    appStore.setGeneratedCode(finalCode)
    // Write directly to editor state so UI updates even if generatedCode watcher misses this cycle.
    if (finalCode.trim()) {
      appStore.setPythonFileContent(finalCode)
    }

    // Display the generated code and any execution results from the backend
    if (finalCode && finalCode.trim()) {
      appStore.setTerminalOutput(response.stdout || response.terminal_output || 'Code generated successfully.')

      // Check for result data from server-side execution
      if (response.plotly_figure || (response.result?.data && response.result?.layout)) {
        appStore.setPlotlyFigure(response.plotly_figure || response.result)
        appStore.setResultData(null)
        appStore.setActiveTab('figure')
      } else if (response.result?.columns && response.result?.data) {
        appStore.setResultData(response.result)
        appStore.setPlotlyFigure(null)
        appStore.setActiveTab('table')
      }
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
