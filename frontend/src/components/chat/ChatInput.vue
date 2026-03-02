<template>
  <div class="space-y-2">
    <!-- Main Input Card (Cursor-style) -->
    <div
      class="relative flex flex-col rounded-2xl border transition-all duration-150"
      style="
        background-color: var(--color-base);
        border-color: var(--color-border);
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
      "
      :style="isFocused ? { borderColor: 'var(--color-border-hover)', boxShadow: '0 0 0 3px color-mix(in srgb, var(--color-text-main) 5%, transparent)' } : {}"
    >
      <!-- Textarea -->
      <textarea
        v-model="question"
        @keydown.enter.prevent="handleSubmit"
        @keydown.shift.enter="handleNewLine"
        @focus="isFocused = true"
        @blur="isFocused = false"
        placeholder="How can I help you today?"
        class="w-full px-4 pt-4 pb-2 resize-none focus:outline-none text-sm leading-relaxed bg-transparent border-none"
        style="color: var(--color-text-main); min-height: 72px;"
        :class="{ 'opacity-60 cursor-not-allowed': !appStore.canAnalyze || appStore.isLoading }"
        :disabled="!appStore.canAnalyze || appStore.isLoading"
      />

      <!-- Bottom Action Row -->
      <div class="flex items-center justify-between px-3 pb-3 pt-1">

        <!-- Left: Add button -->
        <button
          type="button"
          class="btn-icon"
          title="Attach file"
        >
          <PlusIcon class="w-5 h-5" />
        </button>

        <!-- Right: Model selector + action button -->
        <div class="flex items-center gap-3">
          <ModelSelector
            :selected-model="appStore.selectedModel"
            :model-options="appStore.availableModels"
            @model-changed="handleModelChange"
          />

          <!-- Mic (empty) → ArrowUp (has text) -->
          <button
            @click="handleSubmit"
            :disabled="appStore.isLoading || !appStore.canAnalyze"
            class="transition-all duration-150 focus:outline-none"
            :class="
              question.trim().length > 0
                ? 'text-zinc-900 hover:text-zinc-700'
                : 'cursor-default opacity-50'
            "
            :title="question.trim().length > 0 ? 'Send (Enter)' : 'Start typing to send'"
          >
            <!-- Mic icon: empty state -->
            <MicrophoneIcon v-if="question.trim().length === 0" class="w-5 h-5" />
            <!-- Arrow Up icon: text entered -->
            <ArrowUpCircleIcon v-else class="w-6 h-6" />
          </button>
        </div>

      </div>
    </div>

    <!-- Requirements Notice -->
    <div v-if="!appStore.canAnalyze" class="rounded-xl p-4 border" style="background-color: color-mix(in srgb, var(--color-error) 5%, transparent); border-color: color-mix(in srgb, var(--color-error) 20%, transparent);">
      <div class="flex items-start gap-3">
        <ExclamationTriangleIcon class="h-5 w-5 shrink-0 mt-0.5" style="color: var(--color-error);" />
        <div>
          <h4 class="text-sm font-semibold mb-1" style="color: var(--color-error);">Setup Required</h4>
          <ul class="space-y-1 text-sm list-disc list-inside" style="color: var(--color-text-muted);">
            <li>Create or select a workspace from the header dropdown</li>
            <li>Enter your OpenRouter API key in Settings</li>
          </ul>
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
import ModelSelector from '../ui/ModelSelector.vue'
import {
  PlusIcon,
  MicrophoneIcon,
  ExclamationTriangleIcon,
} from '@heroicons/vue/24/outline'
import { ArrowUpCircleIcon } from '@heroicons/vue/24/solid'

const appStore = useAppStore()

const question = ref('')
const isFocused = ref(false)

const canSend = computed(() =>
  appStore.canAnalyze &&
  question.value.trim().length > 0 &&
  question.value.length <= 1000 &&
  !appStore.isLoading
)

function handleModelChange(model) {
  appStore.setSelectedModel(model)
}

function isBrowserVirtualPath(path) {
  const normalized = String(path || '').toLowerCase()
  return normalized.startsWith('browser://') || normalized.startsWith('browser:/') || normalized.startsWith('/browser:/')
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

  appStore.addChatMessage(questionText, '')
  appStore.setLoading(true)

  const abortController = new AbortController()
  const signal = abortController.signal

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

    await ensureWorkspaceDatasetReady(workspaceId)

    warningTimer = setTimeout(() => {
      toast.warning('Request Taking Longer', 'Your query is taking longer than expected.')
    }, 30000)

    cancelTimer = setTimeout(() => {
      toast.error('Request Cancelled', 'Your query took too long and was cancelled.')
      abortController.abort()
    }, 300000)

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

    const { is_safe, code, current_code, explanation } = response
    const finalCode = (code ?? current_code ?? '').toString()

    if (!is_safe) {
      appStore.updateLastMessageExplanation(explanation || 'Your query was flagged as potentially unsafe.')
      return
    }

    appStore.updateLastMessageExplanation(explanation)
    appStore.setGeneratedCode(finalCode)
    if (finalCode.trim()) {
      appStore.setPythonFileContent(finalCode)
    }

    if (finalCode && finalCode.trim()) {
      const executionStderr = response?.execution?.stderr || ''
      const executionStdout = response?.execution?.stdout || ''
      appStore.setTerminalOutput(executionStderr || executionStdout || response.stdout || response.terminal_output || 'Code generated and executed.')

      if (response.plotly_figure || (response.result?.data && response.result?.layout)) {
        appStore.setPlotlyFigure(response.plotly_figure || response.result)
        appStore.setResultData(null)
        appStore.setDataPane('figure')
      } else if (response.result?.columns && response.result?.data) {
        appStore.setResultData(response.result)
        appStore.setPlotlyFigure(null)
        appStore.setDataPane('table')
      }
    }

    const artifactItems = Array.isArray(response?.artifacts) ? response.artifacts : []
    if (artifactItems.length > 0) {
      const dataframeArtifacts = artifactItems
        .filter((item) => String(item?.kind || '') === 'dataframe')
        .map((item) => ({
          name: String(item?.logical_name || 'dataframe'),
          data: {
            artifact_id: item?.artifact_id,
            row_count: Number(item?.row_count || 0),
            columns: Array.isArray(item?.schema) ? item.schema.map((col) => String(col?.name || '')) : [],
            data: Array.isArray(item?.preview_rows) ? item.preview_rows : []
          }
        }))
      const figureArtifacts = artifactItems
        .filter((item) => String(item?.kind || '') === 'figure')
        .map((item) => ({
          name: String(item?.logical_name || 'figure'),
          data: item?.payload?.figure || null
        }))

      appStore.setDataframes(dataframeArtifacts)
      appStore.setFigures(figureArtifacts)
      if (dataframeArtifacts.length > 0) {
        appStore.setResultData(dataframeArtifacts[0].data)
        appStore.setDataPane('table')
      } else if (figureArtifacts.length > 0) {
        appStore.setPlotlyFigure(figureArtifacts[0].data)
        appStore.setDataPane('figure')
      }
    }

    setTimeout(() => {
      const scrollableContainer = document.querySelector('[data-chat-scroll-container]')
      if (scrollableContainer) {
        scrollableContainer.scrollTop = scrollableContainer.scrollHeight
      }
    }, 200)

  } catch (error) {
    console.error('Analysis failed:', error)

    if (warningTimer) clearTimeout(warningTimer)
    if (cancelTimer) clearTimeout(cancelTimer)

    let errorTitle = 'Analysis Failed'
    let errorMessage = 'Failed to generate code. Please try again.'

    if (error.name === 'AbortError' || signal.aborted) {
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
    }

    toast.error(errorTitle, errorMessage)
    appStore.setTerminalOutput(`Error: ${errorMessage}`)
    appStore.updateLastMessageExplanation(errorMessage)
  } finally {
    if (warningTimer) clearTimeout(warningTimer)
    if (cancelTimer) clearTimeout(cancelTimer)
    appStore.setLoading(false)
  }
}

function handleNewLine(event) {
  const textarea = event.target
  const start = textarea.selectionStart
  const end = textarea.selectionEnd

  question.value = question.value.substring(0, start) + '\n' + question.value.substring(end)

  setTimeout(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  }, 0)
}
</script>
