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
import { toast } from '../../composables/useToast'
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
    console.log('📤 Sending request to /chat endpoint:', requestData)

    // Set up timeout timers
    warningTimer = setTimeout(() => {
      toast.warning('Request Taking Longer', 'Your query is taking longer than expected. It will continue processing in the background.')
    }, 30000) // 30 seconds

    cancelTimer = setTimeout(() => {
      toast.error('Request Cancelled', 'Your query took too long and was cancelled. Please try again.')
      abortController.abort()
    }, 300000) // 5 minutes

    // Call the analysis API with abort signal
    const response = await apiService.analyzeData(requestData, signal)

    // Parse the response with new format
    const { is_safe, is_relevant, code, explanation } = response

    // Check if the query is safe and relevant
    if (!is_safe) {
      toast.error('Query Blocked', 'Your query was flagged as potentially unsafe and was not executed.')
      appStore.setTerminalOutput('⚠️ Query was flagged as potentially unsafe and was not executed.')
      appStore.setActiveTab('code')
      return
    }



    // Update the last message with the explanation
    appStore.updateLastMessageExplanation(explanation)
    appStore.setGeneratedCode(code)

    // Trigger scroll to bottom after message is added
    setTimeout(() => {
      // Find the scrollable container directly
      const scrollableContainer = document.querySelector('[data-chat-scroll-container]')
      if (scrollableContainer) {
        scrollableContainer.scrollTop = scrollableContainer.scrollHeight
      }
    }, 200)

    // Determine which tab to show based on available results
    if (response.figure) {
      // If there's a chart, show the chart tab
      appStore.setActiveTab('chart')
    } else if (response.result_df) {
      // If there's table data, show the table tab
      appStore.setActiveTab('table')
    } else {
      // Otherwise show the code tab
      appStore.setActiveTab('code')
    }

    // Clear any previous terminal output
    appStore.setTerminalOutput('')

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
    appStore.setTerminalOutput(`Error: ${error.message || 'Failed to analyze data'}`)

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
