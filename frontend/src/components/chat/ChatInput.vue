<template>
  <div class="space-y-2">
    <!-- Main Input Card (Cursor-style) -->
    <div class="relative">
      <div
        ref="inputCardRef"
        class="chat-composer-surface group/composer relative flex flex-col rounded-xl border"
        :class="{ 'chat-composer-drag-active': isAttachmentDragActive }"
        @dragenter.prevent="handleAttachmentDragEnter"
        @dragover.prevent="handleAttachmentDragOver"
        @dragleave.prevent="handleAttachmentDragLeave"
        @drop.prevent="handleAttachmentDrop"
      >
      <input
        ref="attachmentInputRef"
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        multiple
        class="hidden"
        @change="handleAttachmentSelection"
      />
      <!-- Textarea -->
      <textarea
        ref="textareaRef"
        v-model="question"
        @keydown="handleKeydown"
        @input="handleInputChange"
        @click="handleCaretInteraction"
        @keyup="handleCaretInteraction"
        :placeholder="composerPlaceholder"
        class="w-full px-3 pt-3 pb-1.5 resize-none focus:outline-none text-[13px] leading-[1.55] bg-transparent border-none"
        style="color: var(--color-text-main); min-height: 60px;"
        :class="{ 'opacity-60 cursor-not-allowed': !workspaceActivation.canAnalyze || executionStore.isConversationRunning(conversationStore.activeConversationId) }"
        :disabled="!workspaceActivation.canAnalyze || executionStore.isConversationRunning(conversationStore.activeConversationId)"
      />

      <ChatAttachmentTray
        :attachments="pendingAttachments"
        :format-size="formatAttachmentSize"
        @remove="removePendingAttachment"
      />

      <Transition name="motion-fade">
        <div
          v-if="isAttachmentDragActive"
          class="pointer-events-none absolute inset-3 z-10 flex items-center justify-center rounded-2xl border-2 border-dashed"
          style="border-color: var(--color-border-hover); background-color: color-mix(in srgb, var(--color-base) 80%, transparent);"
        >
          <div class="text-center">
            <PhotoIcon class="mx-auto h-6 w-6" style="color: var(--color-text-main);" />
            <p class="mt-2 text-sm font-medium" style="color: var(--color-text-main);">Drop images to attach</p>
          </div>
        </div>
      </Transition>

      <!-- Bottom Action Row -->
      <ChatComposerActions>
        <div class="flex min-w-0 items-center gap-1.5">
          <button
            type="button"
            class="btn-icon"
            title="Attach images"
            aria-label="Attach images"
            data-tooltip="Attach images"
            @click="openAttachmentPicker"
          >
            <PlusIcon class="w-4 h-4" />
          </button>
        </div>

        <div class="flex min-w-0 flex-1 items-center justify-end gap-2">
          <button
            v-if="isVoiceInputActive"
            type="button"
            class="btn-icon voice-input-pulse"
            title="Stop voice input"
            aria-label="Stop voice input"
            data-tooltip="Stop voice input"
            @click="stopVoiceInput"
          >
            <StopIcon class="h-3.5 w-3.5" />
          </button>
          <button
            v-else
            type="button"
            class="btn-icon"
            :disabled="!canTriggerVoiceInput"
            :title="voiceButtonTitle"
            aria-label="Start voice input"
            data-tooltip="Start voice input"
            @click="startVoiceInput"
          >
            <MicrophoneIcon class="h-3.5 w-3.5" />
          </button>

          <button
            v-if="executionStore.isConversationRunning(conversationStore.activeConversationId)"
            type="button"
            class="composer-action-button focus:outline-none"
            title="Stop generation"
            aria-label="Stop generation"
            data-tooltip="Stop generation"
            @click="handleStopGeneration"
          >
            <StopIcon class="h-3 w-3" />
          </button>
          <button
            v-else
            type="button"
            class="composer-action-button focus:outline-none"
            :disabled="!canSend"
            title="Send message"
            aria-label="Send message"
            data-tooltip="Send message"
            @click="handleSubmit"
          >
            <ArrowUpIcon class="h-3 w-3" />
          </button>
        </div>

      </ChatComposerActions>
      </div>

      <Transition name="motion-popover">
        <div
          v-if="showCommandSuggestions"
          class="motion-popover-surface absolute left-0 right-0 z-[70] overflow-hidden rounded-xl border shadow-lg suggestions-glass"
          :class="suggestionsOpenUp ? 'motion-popover-from-bottom bottom-full mb-2' : 'top-full mt-1'"
          style="border-color: var(--color-border);"
        >
        <ul class="py-1">
          <li v-for="(item, index) in commandSuggestions" :key="item.name">
            <button
              type="button"
              class="flex w-full items-start justify-between gap-3 px-3 py-2 text-left text-sm transition-colors"
              :class="index === selectedCommandIndex ? 'bg-[var(--color-selected-surface)]' : 'hover:bg-[var(--color-surface-subtle)]'"
              @mousedown.prevent="acceptCommandSuggestion(item)"
            >
              <span class="min-w-0">
                <span class="block truncate font-medium" style="color: var(--color-text-main);">/{{ item.name }}</span>
                <span class="block truncate text-xs" style="color: var(--color-text-muted);">{{ item.description }}</span>
              </span>
              <span class="shrink-0 rounded border px-1.5 py-0.5 text-[10px] uppercase" style="color: var(--color-text-muted); border-color: var(--color-border);">
                {{ item.category }}
              </span>
            </button>
          </li>
        </ul>
        </div>
      </Transition>

      <Transition name="motion-popover">
        <ColumnSuggest
          v-if="showColumnSuggestions"
          :items="columnSuggestions"
          :selected-index="selectedColumnIndex"
          :open-up="suggestionsOpenUp"
          @select="acceptColumnSuggestion"
        />
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import { executionApi } from '../../api/execution'
import { workspaceApi } from '../../api/workspaces'
import executionService from '../../services/executionService'
import { executeCommand, getRegisteredCommands, isCommand } from '../../services/commandRegistry'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { deriveConversationTitle } from '../../utils/conversationTitle'
import { normalizePlotlyFigure } from '../../utils/figurePayload'
import { modelSupportsImages, SUPPORTED_CHAT_IMAGE_TYPES } from '../../utils/modelCapabilities'
import ColumnSuggest from './ColumnSuggest.vue'
import ChatAttachmentTray from './ChatAttachmentTray.vue'
import ChatComposerActions from './ChatComposerActions.vue'
import { useChatAttachments } from '../../composables/useChatAttachments'
import { useChatAutocomplete } from '../../composables/useChatAutocomplete'
import { useVoiceInput } from '../../composables/useVoiceInput'
import { useChatStream } from '../../composables/useChatStream'
import { useConversationRunControl } from '../../composables/useConversationRunControl'
import {
  PlusIcon,
  PhotoIcon,
} from '@heroicons/vue/24/outline'
import { ArrowUpIcon, MicrophoneIcon, StopIcon } from '@heroicons/vue/24/solid'

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const chatStream = useChatStream(conversationStore, extractApiErrorMessage)
const runControl = useConversationRunControl(executionStore)
const effectiveWorkspaceModel = computed(() => workspaceStore.workspaceAIConfig?.effective?.main_model || preferencesStore.selectedModel)
const primaryWorkspaceTableName = computed(() => {
  const summaryTable = (Array.isArray(workspaceStore.activeWorkspaceSummary?.table_names)
    ? workspaceStore.activeWorkspaceSummary.table_names
    : []
  ).map((name: any) => String(name || '').trim()).find(Boolean)
  if (summaryTable) return summaryTable
  const catalogItem = (Array.isArray(workspaceStore.columnCatalog) ? workspaceStore.columnCatalog : [])
    .find((item: any) => String(item?.table_name || '').trim())
  return String(catalogItem?.table_name || '').trim()
})
const { formatAttachmentSize } = useChatAttachments()
useChatAutocomplete()
useVoiceInput()

const question = ref('')
const textareaRef = ref<any>(null)
const inputCardRef = ref<any>(null)
const attachmentInputRef = ref<any>(null)
const commandSuggestions = ref<any[]>([])
const selectedCommandIndex = ref(0)
const columnSuggestions = ref<any[]>([])
const selectedColumnIndex = ref(0)
const questionHistoryIndex = ref(-1)
const questionHistoryDraft = ref('')
const activeTokenRange = ref({ start: 0, end: 0, token: '' })
const suggestionsOpenUp = ref(false)
const dismissedSuggestionSignature = ref('')
const pendingAttachments = ref<any[]>([])
const isAttachmentDragActive = ref(false)
const dragDepth = ref(0)
const supportsVoiceInput = ref(false)
const isVoiceInputActive = ref(false)
const speechRecognition = ref<any>(null)
const voiceDraftPrefix = ref('')

const showCommandSuggestions = computed(() => commandSuggestions.value.length > 0)
const showColumnSuggestions = computed(() => columnSuggestions.value.length > 0)
const imageAttachmentsSupported = computed(() => modelSupportsImages(effectiveWorkspaceModel.value))
const composerPlaceholder = computed(() => {
  const tableName = primaryWorkspaceTableName.value
  return tableName ? `Ask about ${tableName}…` : 'Ask about your data…'
})
const canSend = computed(() =>
  workspaceActivation.canAnalyze &&
  (question.value.trim().length > 0 || pendingAttachments.value.length > 0) &&
  question.value.length <= 1000 &&
  !executionStore.isConversationRunning(conversationStore.activeConversationId)
)
const canTriggerVoiceInput = computed(() =>
  workspaceActivation.canAnalyze &&
  supportsVoiceInput.value &&
  !executionStore.isConversationRunning(conversationStore.activeConversationId)
)
const voiceButtonTitle = computed(() => (
  supportsVoiceInput.value
    ? 'Start voice input'
    : 'Voice input unavailable on this device/browser'
))

const DEFAULT_ANALYZE_CANCEL_TIMEOUT_MS = 300000
const FREE_MODEL_ANALYZE_CANCEL_TIMEOUT_MS = 900000
const DEFAULT_SLOW_REQUEST_WARNING_TIMEOUT_MS = 120000


function resolveAnalyzeCancelTimeoutMs(modelId: any) {
  const normalized = String(modelId || '').trim().toLowerCase()
  if (!normalized) return DEFAULT_ANALYZE_CANCEL_TIMEOUT_MS
  if (normalized.includes('/free') || normalized.endsWith('-free') || normalized.includes(':free')) {
    return FREE_MODEL_ANALYZE_CANCEL_TIMEOUT_MS
  }
  return DEFAULT_ANALYZE_CANCEL_TIMEOUT_MS
}

function resolveSlowRequestWarningTimeoutMs(seconds: any) {
  const parsed = Number.parseInt(seconds, 10)
  if (!Number.isFinite(parsed)) return DEFAULT_SLOW_REQUEST_WARNING_TIMEOUT_MS
  const clampedSeconds = Math.min(600, Math.max(5, parsed))
  return clampedSeconds * 1000
}

async function refreshRuntimeStatusAfterExplicitWork(workspaceId: any) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  try {
    const payload = await workspaceApi.runtimeStatus(normalizedWorkspaceId)
    executionStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, payload?.status || 'missing')
  } catch (_error) {
    // Runtime status is informational; keep the completed chat response intact.
  }
}

function parseArtifactTimestampMs(value: any) {
  const raw = String(value || '').trim()
  if (!raw) return 0
  const parsed = Date.parse(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

function sortArtifactsNewestFirst(items: any) {
  if (!Array.isArray(items)) return []
  return [...items].sort((left, right) => {
    const delta = parseArtifactTimestampMs(right?.created_at) - parseArtifactTimestampMs(left?.created_at)
    if (delta !== 0) return delta
    return String(right?.artifact_id || '').localeCompare(String(left?.artifact_id || ''))
  })
}

function buildAttachmentId(file: any) {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${String(file?.name || 'image')}`
}

function openAttachmentPicker() {
  if (!imageAttachmentsSupported.value) {
    toast.error('Images Not Supported', 'The selected model does not support image attachments.')
    return
  }
  attachmentInputRef.value?.click()
}

async function fileToBase64(file: any) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result || '')
      resolve(result.includes(',') ? result.split(',')[1] : result)
    }
    reader.onerror = () => reject(reader.error || new Error('Failed to read image file.'))
    reader.readAsDataURL(file)
  })
}

async function appendPendingAttachments(files: any) {
  if (!imageAttachmentsSupported.value) {
    toast.error('Images Not Supported', 'Switch to a vision-capable model before attaching images.')
    return
  }
  const normalizedFiles = (Array.from(files || []) as File[]).filter((file) => SUPPORTED_CHAT_IMAGE_TYPES.has(String(file.type || '').toLowerCase()))
  if (normalizedFiles.length === 0) {
    toast.error('Unsupported File', 'Only PNG, JPG, WEBP, and GIF images can be attached.')
    return
  }

  for (const file of normalizedFiles) {
    const dataBase64 = await fileToBase64(file)
    pendingAttachments.value.push({
      attachment_id: buildAttachmentId(file),
      filename: String(file.name || 'image'),
      media_type: String(file.type || 'image/png'),
      data_base64: dataBase64,
      preview_url: `data:${String(file.type || 'image/png')};base64,${dataBase64}`,
      size: Number(file.size || 0),
    })
  }
}

async function handleAttachmentSelection(event: any) {
  try {
    await appendPendingAttachments(event?.target?.files || [])
  } catch (error: any) {
    toast.error('Image Attach Failed', extractApiErrorMessage(error, 'Failed to attach image.'))
  } finally {
    if (event?.target) event.target.value = ''
  }
}

function removePendingAttachment(attachmentId: any) {
  const targetId = String(attachmentId || '').trim()
  pendingAttachments.value = pendingAttachments.value.filter(
    (item) => String(item?.attachment_id || '') !== targetId
  )
}

function handleAttachmentDragEnter() {
  dragDepth.value += 1
  if (!imageAttachmentsSupported.value) return
  isAttachmentDragActive.value = true
}

function handleAttachmentDragOver() {
  if (!imageAttachmentsSupported.value) return
  isAttachmentDragActive.value = true
}

function handleAttachmentDragLeave() {
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (dragDepth.value === 0) {
    isAttachmentDragActive.value = false
  }
}

async function handleAttachmentDrop(event: any) {
  dragDepth.value = 0
  isAttachmentDragActive.value = false
  try {
    await appendPendingAttachments(event?.dataTransfer?.files || [])
  } catch (error: any) {
    toast.error('Image Attach Failed', extractApiErrorMessage(error, 'Failed to attach image.'))
  }
}

function initializeVoiceInput() {
  if (typeof window === 'undefined') return
  const speechWindow = window as any
  const SpeechRecognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition
  if (!SpeechRecognition) {
    supportsVoiceInput.value = false
    speechRecognition.value = null
    return
  }

  try {
    const recognition = new SpeechRecognition()
    recognition.lang = navigator?.language || 'en-US'
    recognition.interimResults = true
    recognition.continuous = true
    recognition.maxAlternatives = 1
    recognition.onstart = () => {
      isVoiceInputActive.value = true
    }
    recognition.onend = () => {
      isVoiceInputActive.value = false
    }
    recognition.onerror = (event: any) => {
      isVoiceInputActive.value = false
      const errorCode = String(event?.error || 'unknown')
      if (errorCode === 'not-allowed' || errorCode === 'service-not-allowed') {
        toast.error('Voice Input Blocked', 'Microphone permission is required for voice input.')
        return
      }
      if (errorCode !== 'aborted') {
        toast.error('Voice Input Error', `Voice input failed (${errorCode}).`)
      }
    }
    recognition.onresult = (event: any) => {
      const transcriptParts = []
      for (let i = 0; i < event.results.length; i += 1) {
        const text = String(event.results[i]?.[0]?.transcript || '').trim()
        if (text) transcriptParts.push(text)
      }
      const spokenText = transcriptParts.join(' ').trim()
      const prefix = voiceDraftPrefix.value.trim()
      question.value = spokenText ? (prefix ? `${prefix} ${spokenText}` : spokenText) : prefix
      nextTick(() => {
        if (textareaRef.value) {
          textareaRef.value.focus()
          const caret = question.value.length
          textareaRef.value.selectionStart = caret
          textareaRef.value.selectionEnd = caret
        }
        void updateAutocompleteSuggestions()
      })
    }
    speechRecognition.value = recognition
    supportsVoiceInput.value = true
  } catch (_error) {
    supportsVoiceInput.value = false
    speechRecognition.value = null
  }
}

function startVoiceInput() {
  if (!speechRecognition.value || !supportsVoiceInput.value) return
  voiceDraftPrefix.value = question.value.trim()
  try {
    speechRecognition.value.start()
  } catch (_error) {
    isVoiceInputActive.value = false
  }
}

function stopVoiceInput() {
  if (!speechRecognition.value) return
  try {
    speechRecognition.value.stop()
  } catch (_error) {
    isVoiceInputActive.value = false
  }
}

function handleStopGeneration() {
  runControl.stopConversation(conversationStore.activeConversationId)
}

function isSimpleIdentifier(value: any) {
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(String(value || '').trim())
}

function quoteSqlIdentifier(value: any) {
  return `"${String(value || '').replace(/"/g, '""')}"`
}

function buildColumnReference(tableName: any, columnName: any) {
  const table = String(tableName || '').trim()
  const column = String(columnName || '').trim()
  if (!table || !column) return ''
  if (isSimpleIdentifier(column)) {
    return `${table}.${column}`
  }
  return `${table}.${quoteSqlIdentifier(column)}`
}

function buildColumnSuggestion(item: any) {
  const tableName = String(item?.table_name || '').trim()
  const columnName = String(item?.column_name || '').trim()
  if (!tableName || !columnName) return null

  const displayText = buildColumnReference(tableName, columnName)
  return {
    ...item,
    table_name: tableName,
    column_name: columnName,
    dtype: String(item?.dtype || ''),
    displayText,
    insertText: displayText,
    dotText: `${tableName}.${columnName}`,
    isSpecial: !isSimpleIdentifier(columnName),
  }
}

function collectColumnCandidates() {
  const merged: any[] = []
  const seen = new Set()

  const addCandidate = (tableName: any, columnName: any, dtype = '') => {
    const table = String(tableName || '').trim()
    const column = String(columnName || '').trim()
    if (!table || !column) return
    const key = `${table.toLowerCase()}::${column.toLowerCase()}`
    if (seen.has(key)) return
    seen.add(key)
    const suggestion = buildColumnSuggestion({
      table_name: table,
      column_name: column,
      dtype: String(dtype || ''),
    })
    if (suggestion) merged.push(suggestion)
  }

  const catalogItems = Array.isArray(workspaceStore.columnCatalog) ? workspaceStore.columnCatalog : []
  catalogItems.forEach((item: any) => {
    addCandidate(item?.table_name, item?.column_name, item?.dtype)
  })

  return merged
}

function clearSuggestions() {
  commandSuggestions.value = []
  selectedCommandIndex.value = 0
  columnSuggestions.value = []
  selectedColumnIndex.value = 0
}

function updateSuggestionPlacement() {
  const target = inputCardRef.value || textareaRef.value
  if (!target) {
    suggestionsOpenUp.value = false
    return
  }
  const rect = target.getBoundingClientRect()
  const minDropdownHeight = 220
  const spaceBelow = Math.max(0, window.innerHeight - rect.bottom)
  suggestionsOpenUp.value = spaceBelow < minDropdownHeight
}

function currentCursorPosition() {
  const target = textareaRef.value
  if (!target) return question.value.length
  return Number(target.selectionStart || 0)
}

function tokenRangeAtCursor(text: any, cursor: any) {
  const safeText = String(text || '')
  const safeCursor = Math.max(0, Math.min(Number(cursor || 0), safeText.length))
  const prefix = safeText.slice(0, safeCursor)
  const match = prefix.match(/([^\s]*)$/)
  const token = String(match?.[1] || '')
  return {
    start: safeCursor - token.length,
    end: safeCursor,
    token,
  }
}

function buildSuggestionDismissSignature(text = question.value, cursor = currentCursorPosition()) {
  const safeText = String(text || '')
  const range = tokenRangeAtCursor(safeText, cursor)
  const token = String(range.token || '').trim()
  return `${range.start}:${range.end}:${token}:${safeText}`
}

function applyTokenReplacement(replacement: any, { appendSpace = false } = {}) {
  const value = String(question.value || '')
  const { start, end } = activeTokenRange.value
  const safeStart = Math.max(0, Math.min(start, value.length))
  const safeEnd = Math.max(safeStart, Math.min(end, value.length))
  const suffix = appendSpace ? ' ' : ''
  const updated = `${value.slice(0, safeStart)}${replacement}${suffix}${value.slice(safeEnd)}`
  question.value = updated
  const caret = safeStart + replacement.length + suffix.length
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.focus()
      textareaRef.value.selectionStart = caret
      textareaRef.value.selectionEnd = caret
    }
    void updateAutocompleteSuggestions()
  })
}

function acceptCommandSuggestion(item: any = null) {
  const selected = item || commandSuggestions.value[selectedCommandIndex.value]
  if (!selected) return
  applyTokenReplacement(`/${selected.name}`, { appendSpace: true })
  clearSuggestions()
}

function acceptColumnSuggestion(item: any = null) {
  const selected = item || columnSuggestions.value[selectedColumnIndex.value]
  if (!selected) return
  applyTokenReplacement(String(selected.insertText || `${selected.table_name}.${selected.column_name}`))
  clearSuggestions()
}

function navigateSuggestion(step: any) {
  if (showCommandSuggestions.value) {
    const size = commandSuggestions.value.length
    if (!size) return
    selectedCommandIndex.value = (selectedCommandIndex.value + step + size) % size
    return
  }
  if (showColumnSuggestions.value) {
    const size = columnSuggestions.value.length
    if (!size) return
    selectedColumnIndex.value = (selectedColumnIndex.value + step + size) % size
  }
}

async function updateAutocompleteSuggestions() {
  const value = String(question.value || '')
  const range = tokenRangeAtCursor(value, currentCursorPosition())
  activeTokenRange.value = range

  const token = String(range.token || '').trim()
  const signature = `${range.start}:${range.end}:${token}:${value}`
  if (
    dismissedSuggestionSignature.value &&
    dismissedSuggestionSignature.value === signature
  ) {
    clearSuggestions()
    return
  }
  if (dismissedSuggestionSignature.value && dismissedSuggestionSignature.value !== signature) {
    dismissedSuggestionSignature.value = ''
  }

  if (!token) {
    clearSuggestions()
    return
  }

  if (token.startsWith('/')) {
    const prefixBeforeToken = value.slice(0, range.start)
    if (prefixBeforeToken.trim().length > 0) {
      clearSuggestions()
      return
    }

    const prefix = token.slice(1).toLowerCase()
    commandSuggestions.value = getRegisteredCommands()
      .filter((item) => !prefix || item.name.startsWith(prefix))
      .slice(0, 8)
    selectedCommandIndex.value = 0
    columnSuggestions.value = []
    selectedColumnIndex.value = 0
    updateSuggestionPlacement()
    return
  }

  if (!Array.isArray(workspaceStore.columnCatalog) || workspaceStore.columnCatalog.length === 0) {
    await workspaceStore.fetchColumnCatalog()
  }

  const normalizedToken = token.toLowerCase()
  columnSuggestions.value = collectColumnCandidates()
    .filter((item) => {
      const searchPool = [
        String(item.displayText || ''),
        String(item.dotText || ''),
        String(item.column_name || ''),
        String(item.table_name || ''),
      ].map((entry) => entry.toLowerCase())
      return (
        searchPool.some((entry) => entry.startsWith(normalizedToken)) ||
        searchPool.some((entry) => entry.includes(normalizedToken))
      )
    })
    .slice(0, 8)
  selectedColumnIndex.value = 0
  commandSuggestions.value = []
  updateSuggestionPlacement()
}

function handleInputChange() {
  if (questionHistoryIndex.value !== -1) {
    questionHistoryIndex.value = -1
    questionHistoryDraft.value = ''
  }
  void updateAutocompleteSuggestions()
}

const SUGGESTION_NAVIGATION_KEYS = new Set(['ArrowDown', 'ArrowUp', 'Tab', 'Enter', 'Escape'])

function handleCaretInteraction(event: any = null) {
  if (
    event &&
    SUGGESTION_NAVIGATION_KEYS.has(String(event.key || '')) &&
    (showCommandSuggestions.value || showColumnSuggestions.value)
  ) {
    return
  }
  void updateAutocompleteSuggestions()
}

function setQuestionFromHistory(value: any) {
  question.value = String(value || '')
  clearSuggestions()
  nextTick(() => {
    if (textareaRef.value) {
      const caret = question.value.length
      textareaRef.value.focus()
      textareaRef.value.selectionStart = caret
      textareaRef.value.selectionEnd = caret
    }
  })
}

function isHistoryNavigationAllowed(event: any, step: any) {
  if (!event) return false
  if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return false
  if (showCommandSuggestions.value || showColumnSuggestions.value) return false
  const textarea = textareaRef.value
  if (!textarea) return false
  if (textarea.selectionStart !== textarea.selectionEnd) return false
  const caret = Number(textarea.selectionStart || 0)
  if (step < 0) return caret === 0
  if (step > 0) return caret === String(question.value || '').length && questionHistoryIndex.value !== -1
  return false
}

function navigateQuestionHistory(step: any) {
  const history = Array.isArray(conversationStore.questionHistory) ? conversationStore.questionHistory : []
  if (history.length === 0) return false

  if (step < 0) {
    if (questionHistoryIndex.value === -1) {
      questionHistoryDraft.value = question.value
      questionHistoryIndex.value = history.length - 1
    } else if (questionHistoryIndex.value > 0) {
      questionHistoryIndex.value -= 1
    }
    setQuestionFromHistory(history[questionHistoryIndex.value] || '')
    return true
  }

  if (step > 0) {
    if (questionHistoryIndex.value === -1) return false
    if (questionHistoryIndex.value < history.length - 1) {
      questionHistoryIndex.value += 1
      setQuestionFromHistory(history[questionHistoryIndex.value] || '')
      return true
    }
    const draft = questionHistoryDraft.value
    questionHistoryIndex.value = -1
    questionHistoryDraft.value = ''
    setQuestionFromHistory(draft)
    return true
  }

  return false
}

function handleKeydown(event: any) {
  if (!event) return

  if ((showCommandSuggestions.value || showColumnSuggestions.value) && event.key === 'ArrowDown') {
    event.preventDefault()
    navigateSuggestion(1)
    return
  }
  if ((showCommandSuggestions.value || showColumnSuggestions.value) && event.key === 'ArrowUp') {
    event.preventDefault()
    navigateSuggestion(-1)
    return
  }
  if ((showCommandSuggestions.value || showColumnSuggestions.value) && event.key === 'Tab') {
    event.preventDefault()
    if (showCommandSuggestions.value) {
      acceptCommandSuggestion()
    } else {
      acceptColumnSuggestion()
    }
    return
  }
  if ((showCommandSuggestions.value || showColumnSuggestions.value) && event.key === 'Escape') {
    event.preventDefault()
    dismissedSuggestionSignature.value = buildSuggestionDismissSignature()
    clearSuggestions()
    return
  }
  if (event.key === 'ArrowUp' && isHistoryNavigationAllowed(event, -1)) {
    const didNavigateHistory = navigateQuestionHistory(-1)
    if (didNavigateHistory) {
      event.preventDefault()
      return
    }
  }
  if (event.key === 'ArrowDown' && isHistoryNavigationAllowed(event, 1)) {
    const didNavigateHistory = navigateQuestionHistory(1)
    if (didNavigateHistory) {
      event.preventDefault()
      return
    }
  }

  if (event.key === 'Enter') {
    event.preventDefault()
    if (event.shiftKey) {
      handleNewLine(event)
      return
    }
    handleSubmit()
  }
}

function applyCommandResultToStore(commandResult: any) {
  const payload = commandResult?.result && typeof commandResult.result === 'object'
    ? commandResult.result
    : null
  const columns = Array.isArray(payload?.columns) ? payload.columns.map((col: any) => String(col)) : []
  const rows = Array.isArray(payload?.data) ? payload.data : []
  const hasTablePayload = columns.length > 0

  if (hasTablePayload) {
    const tableResult = {
      columns,
      data: rows,
      row_count: Number.isFinite(Number(payload?.row_count)) ? Number(payload.row_count) : rows.length,
      result_type: String(payload?.result_type || commandResult?.result_type || 'table'),
    }
    artifactStore.setDataframes([
      {
        name: String(commandResult?.name || 'command_result'),
        origin: 'ai',
        data: tableResult,
      },
    ])
    artifactStore.setResultData(tableResult)
    artifactStore.setFigures([])
    artifactStore.setPlotlyFigure(null)
    artifactPresentation.revealArtifactsPane({ hasDataframes: true })
    uiStore.setActiveTab('table')
  } else {
    artifactStore.setDataframes([])
    artifactStore.setResultData(null)
    artifactStore.setFigures([])
    artifactStore.setPlotlyFigure(null)
  }

  const output = String(commandResult?.output || `/${commandResult?.name || 'command'} executed.`)
  executionStore.setTerminalOutput(output)
  executionStore.appendTerminalEntry({
    kind: 'output',
    source: 'analysis',
    origin: 'ai',
    conversationId: String(conversationStore.activeConversationId || ''),
    label: `/${String(commandResult?.name || 'command')}`,
    command: `/${String(commandResult?.name || 'command')}`,
    status: 'success',
    stdout: output,
    stderr: '',
    exitCode: 0,
  })
}

function appendChatExecutionOutput(response: any, conversationId = conversationStore.activeConversationId, code = '') {
  const execution = response?.execution && typeof response.execution === 'object'
    ? response.execution
    : null
  if (!execution) return false

  const stdout = String(execution.stdout || response?.stdout || response?.terminal_output || '')
  const stderr = String(execution.stderr || execution.error || '')
  const scalarResult = normalizeScalarResult(response)
  const artifacts = Array.isArray(response?.artifacts) ? response.artifacts : []
  const hasTableOutput = Boolean(
    (response?.result?.columns && response?.result?.data)
    || artifacts.some((item: any) => String(item?.kind || '').toLowerCase() === 'dataframe'),
  )
  const hasChartOutput = Boolean(
    normalizePlotlyFigure(response?.plotly_figure || response?.result)
    || artifacts.some((item: any) => String(item?.kind || '').toLowerCase() === 'figure'),
  )
  const hasOutput = Boolean(stdout.trim() || stderr.trim() || scalarResult)
  if (!hasOutput) return false

  const success = execution.success !== false && String(execution.status || 'success').toLowerCase() !== 'failed'
  const terminalOutput = stderr || stdout
  if (String(conversationId || '').trim() === String(conversationStore.activeConversationId || '').trim()) {
    executionStore.setTerminalOutput(terminalOutput)
    executionStore.appendTerminalEntry({
      kind: 'output',
      source: 'analysis',
      origin: 'ai',
      conversationId: String(conversationId || ''),
      label: execution.output_truncated ? 'Run output (truncated)' : 'Run output',
      command: String(code || ''),
      runId: String(response?.run_id || ''),
      status: success ? 'success' : 'error',
      stdout,
      stderr,
      exitCode: success ? 0 : 1,
      durationMs: Number.isFinite(Number(execution.duration_ms)) ? Number(execution.duration_ms) : null,
      truncated: Boolean(execution.output_truncated),
      scalarOutputs: scalarResult ? [scalarResult] : [],
      hasTableOutput,
      hasChartOutput,
    })
  } else {
    conversationStore.patchConversationState(conversationId, { terminalOutput })
  }
  return true
}

function scalarDisplayValue(value: any) {
  if (value === undefined) return ''
  if (value === null) return 'null'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value)
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch (_error) {
    return String(value)
  }
}

function normalizeScalarResult(response: any) {
  const execution = response?.execution && typeof response.execution === 'object'
    ? response.execution
    : {}
  const resultKind = String(execution?.result_kind || response?.result_kind || '').trim().toLowerCase()
  const resultType = String(execution?.result_type || response?.result_type || '').trim()
  const hasExecutionResult = Object.prototype.hasOwnProperty.call(execution, 'result')
  const hasResponseResult = Object.prototype.hasOwnProperty.call(response || {}, 'result')
  if (resultKind !== 'scalar' && resultType.toLowerCase() !== 'scalar') return null
  const value = hasExecutionResult ? execution.result : (hasResponseResult ? response.result : undefined)
  if (value === undefined) return null
  return {
    name: String(execution?.result_name || response?.result_name || 'result'),
    value,
    display_value: scalarDisplayValue(value),
    result_type: resultType || typeof value,
    run_id: String(execution?.run_id || response?.run_id || ''),
    created_at: new Date().toISOString(),
  }
}

function preferredDataPane(payload: any = {}) {
  if (payload?.hasFigures) return 'figure'
  if (payload?.hasDataframes) return 'table'
  if (payload?.hasOutput) return 'output'
  return uiStore.dataPane || 'table'
}

function applyConversationResultState(conversationId: any, statePatch: any = {}, revealPayload: any = {}) {
  const targetConversationId = String(conversationId || '').trim()
  if (!targetConversationId) return
  const active = targetConversationId === String(conversationStore.activeConversationId || '').trim()
  if (active) {
    if (Object.prototype.hasOwnProperty.call(statePatch, 'generatedCode')) executionStore.setGeneratedCode(statePatch.generatedCode)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'pythonFileContent')) executionStore.setPythonFileContent(statePatch.pythonFileContent)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'resultData')) artifactStore.setResultData(statePatch.resultData)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'plotlyFigure')) artifactStore.setPlotlyFigure(statePatch.plotlyFigure)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'dataframes')) artifactStore.setDataframes(statePatch.dataframes)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'figures')) artifactStore.setFigures(statePatch.figures)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'scalars')) artifactStore.setScalars(statePatch.scalars)
    if (Object.prototype.hasOwnProperty.call(statePatch, 'terminalOutput')) executionStore.setTerminalOutput(statePatch.terminalOutput)
    artifactPresentation.revealArtifactsPane(revealPayload)
    return
  }
  conversationStore.patchConversationState(targetConversationId, {
    ...statePatch,
    dataPane: preferredDataPane(revealPayload),
  })
}

async function handleSlashCommand(questionText: any) {
  let commandMessageCreated = false
  let requestConversationId = ''
  let operationId = ''
  let commandFailed = false
  try {
    const workspaceId = workspaceStore.activeWorkspaceId
    if (!workspaceId) {
      throw new Error('Create/select a workspace before analysis.')
    }

    requestConversationId = String(await conversationStore.ensureActiveConversation(
      workspaceStore.activeWorkspaceId,
      deriveConversationTitle(questionText),
    ) || '').trim()
    if (!requestConversationId) {
      throw new Error('Could not create a chat for this command.')
    }
    executionStore.setConversationRun(requestConversationId, {
      status: 'running',
      requestId: `command-${Date.now()}`,
      startedAt: new Date().toISOString(),
    })
    operationId = executionStore.startBackgroundOperation({
      id: `chat-command-${requestConversationId}`,
      type: 'chat',
      title: 'Running command',
      message: 'Executing chat command...',
      priority: 70,
    })
    conversationStore.addChatMessage(questionText, 'Running command...', { conversationId: requestConversationId })
    commandMessageCreated = true
    const result = await executeCommand(questionText, { workspaceStore, conversationStore, executionService })
    const persistedConversationId = String(result?.conversation_id || '').trim()
    if (
      persistedConversationId &&
      persistedConversationId !== String(conversationStore.activeConversationId || '').trim() &&
      requestConversationId === String(conversationStore.activeConversationId || '').trim()
    ) {
      conversationStore.setActiveConversationId(persistedConversationId)
    }
    if (persistedConversationId) {
      await conversationStore.fetchConversations(workspaceStore.activeWorkspaceId)
      await conversationStore.loadWorkspaceTurnTree(workspaceStore.activeWorkspaceId)
      try {
        await conversationStore.fetchActiveConversationUsage(persistedConversationId)
      } catch (_error) {
        // Usage display is informational; command output should still render.
      }
    }
    conversationStore.updateLastMessageExplanation(
      String(result?.output || `/${String(result?.name || 'command')} executed.`),
      null,
      { conversationId: requestConversationId },
    )
    if (requestConversationId === String(conversationStore.activeConversationId || '').trim()) {
      applyCommandResultToStore(result)
    }
  } catch (error: any) {
    commandFailed = true
    const message = extractApiErrorMessage(error, 'Failed to run command.')
    if (commandMessageCreated) {
      conversationStore.updateLastMessageExplanation(`Command failed: ${message}`, null, { conversationId: requestConversationId })
    }
    toast.error('Command Failed', message)
    if (requestConversationId === String(conversationStore.activeConversationId || '').trim()) {
      executionStore.setTerminalOutput(`Error: ${message}`)
      executionStore.appendTerminalEntry({
        kind: 'output',
        source: 'analysis',
        origin: 'ai',
        conversationId: String(requestConversationId || ''),
        label: 'Command error',
        command: String(questionText || ''),
        status: 'error',
        stdout: '',
        stderr: message,
        exitCode: 1,
      })
    } else {
      conversationStore.patchConversationState(requestConversationId, {
        terminalOutput: `Error: ${message}`,
        dataPane: 'output',
      })
    }
  } finally {
    if (requestConversationId) {
      executionStore.setConversationRun(requestConversationId, null)
    }
    if (operationId) {
      executionStore.finishBackgroundOperation(operationId, {
        status: commandFailed ? 'failed' : 'complete',
        title: commandFailed ? 'Command failed' : 'Command complete',
        message: commandFailed ? 'Chat command failed.' : 'Chat command finished.',
      })
    }
  }
}

async function handleSubmit() {
  if (!canSend.value) return
  if (isVoiceInputActive.value) {
    stopVoiceInput()
  }
  if (pendingAttachments.value.length > 0 && !imageAttachmentsSupported.value) {
    toast.error('Images Not Supported', 'The selected model does not support image attachments.')
    return
  }

  const rawQuestionText = question.value.trim()
  const questionText = rawQuestionText || 'Please analyze the attached image(s).'
  const attachmentsPayload = pendingAttachments.value.map((item) => ({
    attachment_id: item.attachment_id,
    filename: item.filename,
    media_type: item.media_type,
    data_base64: item.data_base64,
  }))
  if (rawQuestionText) {
    conversationStore.addQuestionHistoryEntry(questionText)
  }
  questionHistoryIndex.value = -1
  questionHistoryDraft.value = ''
  question.value = ''
  clearSuggestions()
  pendingAttachments.value = []

  if (isCommand(questionText)) {
    if (attachmentsPayload.length > 0) {
      toast.error('Slash Commands Do Not Support Images', 'Remove attached images before running a slash command.')
      pendingAttachments.value = attachmentsPayload.map((item) => ({
        ...item,
        preview_url: `data:${item.media_type};base64,${item.data_base64}`,
        size: 0,
      }))
      question.value = rawQuestionText
      return
    }
    await handleSlashCommand(questionText)
    return
  }

  let requestConversationId = ''
  try {
    requestConversationId = String(await conversationStore.ensureActiveConversation(
      workspaceStore.activeWorkspaceId,
      deriveConversationTitle(questionText),
    ) || '').trim()
  } catch (error: any) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Could not create a chat.'))
    question.value = rawQuestionText
    pendingAttachments.value = attachmentsPayload.map((item) => ({
      ...item,
      preview_url: `data:${item.media_type};base64,${item.data_base64}`,
      size: 0,
    }))
    return
  }
  if (!requestConversationId) {
    toast.error('Conversation Error', 'Could not create a chat.')
    question.value = rawQuestionText
    return
  }
  if (executionStore.isConversationRunning(requestConversationId)) {
    toast.warning('Conversation Running', 'Wait for this conversation to finish before sending another prompt.')
    return
  }
  const localMessageId = `pending-${Date.now()}-${Math.random().toString(36).slice(2)}`
  conversationStore.addChatMessage(questionText, '', { attachments: attachmentsPayload, localMessageId, conversationId: requestConversationId })
  conversationStore.syncLiveTokenUsageFromChatHistory({ conversationId: requestConversationId })
  const operationId = executionStore.startBackgroundOperation({
    id: `chat-stream-${requestConversationId}`,
    type: 'chat',
    title: 'Generating response',
    message: 'Streaming chat response...',
    priority: 80,
  })
  let operationStatus = 'complete'
  let operationMessage = 'Chat response finished.'

  const abortController = new AbortController()
  executionStore.setConversationRun(requestConversationId, {
    status: 'running',
    requestId: localMessageId,
    startedAt: new Date().toISOString(),
    abortController,
  })
  const signal = abortController.signal

  let warningTimer = null
  let cancelTimer = null

  try {
    const workspaceId = workspaceStore.activeWorkspaceId
    if (!workspaceId) {
      throw new Error('Create/select a workspace before analysis.')
    }

    const warningAfterMs = resolveSlowRequestWarningTimeoutMs(preferencesStore.slowRequestWarningSeconds)
    warningTimer = setTimeout(() => {
      toast.warning('Request Taking Longer', 'Your query is taking longer than expected.')
    }, warningAfterMs)

    const cancelAfterMs = resolveAnalyzeCancelTimeoutMs(effectiveWorkspaceModel.value)
    cancelTimer = setTimeout(() => {
      toast.error('Request Cancelled', 'Your query took too long and was cancelled.')
      abortController.abort()
    }, cancelAfterMs)

    let response: any
    const selectedParentTurnId = String(conversationStore.activeTurnId || '').trim()
    response = await executionApi.analyze(
      {
        workspace_id: workspaceId,
        conversation_id: requestConversationId,
        question: questionText,
        current_code: executionStore.pythonFileContent || '',
        model: effectiveWorkspaceModel.value,
        context: workspaceStore.schemaContext.trim() || null,
        use_selected_turn_context: Boolean(selectedParentTurnId),
        selected_parent_turn_id: selectedParentTurnId || null,
        attachments: attachmentsPayload,
        api_key: null
      },
      {
        signal,
        onEvent: (event: any) => chatStream.applyStreamEvent(event, localMessageId, requestConversationId)
      }
    )

    if (
      response?.conversation_id &&
      response.conversation_id !== conversationStore.activeConversationId &&
      requestConversationId === String(conversationStore.activeConversationId || '').trim()
    ) {
      conversationStore.setActiveConversationId(response.conversation_id)
      await conversationStore.fetchConversations(workspaceStore.activeWorkspaceId)
    }

    const responseTurnId = String(response?.turn_id || '').trim()
    if (responseTurnId) {
      conversationStore.setLastMessageTurnId(responseTurnId, localMessageId, { conversationId: requestConversationId })
      if (String(response?.conversation_id || requestConversationId) === String(conversationStore.activeConversationId || '')) {
        await conversationStore.loadActiveTurnRelations(responseTurnId)
        await conversationStore.loadFinalTurn()
      }
      await conversationStore.loadWorkspaceTurnTree(workspaceStore.activeWorkspaceId)
    }

    const { is_safe, code, current_code, explanation, result_explanation, code_explanation } = response
    const finalCode = (code ?? current_code ?? '').toString()
    conversationStore.setLastMessageAnalysisMetadata(response?.metadata || {}, localMessageId, { conversationId: requestConversationId })
    try {
      await conversationStore.fetchActiveConversationUsage(String(response?.conversation_id || requestConversationId || '').trim())
    } catch (_error) {
      // Usage display is informational; the completed response should still render.
    }
    const finalExplanation = (result_explanation ?? explanation ?? '').toString()
    conversationStore.setLastMessageCodeSnapshot(finalCode, localMessageId, { conversationId: requestConversationId })
    conversationStore.setLastMessageCodeExplanation((code_explanation ?? '').toString(), localMessageId, { conversationId: requestConversationId })

    if (!is_safe) {
      conversationStore.updateLastMessageExplanation(finalExplanation || 'Your query was flagged as potentially unsafe.', localMessageId, { conversationId: requestConversationId })
      return
    }

    conversationStore.finalizeLastMessageExplanation(finalExplanation, localMessageId, { conversationId: requestConversationId })
    const finalStatePatch: Record<string, any> = {}
    if (finalCode.trim()) {
      finalStatePatch.generatedCode = finalCode
      finalStatePatch.pythonFileContent = finalCode
      finalStatePatch.userEditedCode = ''
      finalStatePatch.hasUserEditedCode = false
      finalStatePatch.codeEditorSource = 'agent'
    }

    if (finalCode && finalCode.trim()) {
      const hasChatExecutionOutput = appendChatExecutionOutput(response, requestConversationId, finalCode)

      const inlineFigure = normalizePlotlyFigure(response.plotly_figure || response.result)
      if (inlineFigure) {
        finalStatePatch.plotlyFigure = inlineFigure
        finalStatePatch.resultData = null
        finalStatePatch.figures = [{
          name: String(response?.result_name || 'figure'),
          origin: 'ai',
          runId: String(response?.run_id || ''),
          data: inlineFigure,
        }]
        finalStatePatch.figureCount = 1
        applyConversationResultState(requestConversationId, finalStatePatch, { hasFigures: true })
      } else if (response.result?.columns && response.result?.data) {
        finalStatePatch.resultData = response.result
        finalStatePatch.plotlyFigure = null
        finalStatePatch.dataframes = [{
          name: String(response?.result_name || 'result'),
          origin: 'ai',
          runId: String(response?.run_id || ''),
          data: response.result,
        }]
        applyConversationResultState(requestConversationId, finalStatePatch, { hasDataframes: true })
      } else if (hasChatExecutionOutput) {
        applyConversationResultState(requestConversationId, finalStatePatch)
      } else if (Object.keys(finalStatePatch).length > 0) {
        applyConversationResultState(requestConversationId, finalStatePatch)
      }
    }

    const artifactItems = sortArtifactsNewestFirst(Array.isArray(response?.artifacts) ? response.artifacts : [])
    const inlineScalarResult = normalizeScalarResult(response)
    if (artifactItems.length === 0 && !inlineScalarResult) {
      finalStatePatch.scalars = []
    }
    if (artifactItems.length > 0) {
      const dataframeArtifacts = artifactItems
        .filter((item) => String(item?.kind || '') === 'dataframe')
        .map((item) => ({
          name: String(item?.display_name || item?.logical_name || 'dataframe'),
          origin: 'ai',
          runId: String(response?.run_id || ''),
          data: {
            artifact_id: item?.artifact_id,
            logical_name: item?.logical_name || undefined,
            display_name: item?.display_name || undefined,
            row_count: Number(item?.row_count || 0),
            columns: Array.isArray(item?.schema) ? item.schema.map((col: any) => String(col?.name || '')) : [],
            data: Array.isArray(item?.preview_rows) ? item.preview_rows : [],
            created_at: String(item?.created_at || ''),
          }
        }))
      const figureArtifacts = artifactItems
        .filter((item) => String(item?.kind || '') === 'figure')
        .map((item) => {
          const figure = normalizePlotlyFigure(item?.payload?.figure ?? item?.payload)
          if (!figure) return null
          return {
            name: String(item?.display_name || item?.logical_name || 'figure'),
            origin: 'ai',
            runId: String(response?.run_id || ''),
            artifact_id: item?.artifact_id || null,
            logical_name: item?.logical_name || undefined,
            display_name: item?.display_name || undefined,
            created_at: String(item?.created_at || ''),
            data: figure,
          }
        })
        .filter(Boolean)
      const scalarArtifacts = artifactItems
        .filter((item) => String(item?.kind || '') === 'scalar')
        .map((item) => {
          const payload = item?.payload && typeof item.payload === 'object' && !Array.isArray(item.payload) ? item.payload : {}
          const hasPayloadValue = Object.prototype.hasOwnProperty.call(payload, 'value')
          const value = hasPayloadValue ? payload.value : item?.payload
          return {
            name: String(item?.display_name || item?.logical_name || item?.name || 'scalar'),
            origin: 'ai',
            runId: String(response?.run_id || ''),
            artifact_id: item?.artifact_id || null,
            logical_name: item?.logical_name || undefined,
            display_name: item?.display_name || undefined,
            created_at: String(item?.created_at || ''),
            value,
            display_value: scalarDisplayValue(value),
            result_type: String(payload?.type || typeof value),
          }
        })

      finalStatePatch.dataframes = dataframeArtifacts
      finalStatePatch.figures = figureArtifacts
      finalStatePatch.scalars = inlineScalarResult ? [...scalarArtifacts, inlineScalarResult] : scalarArtifacts
      finalStatePatch.figureCount = figureArtifacts.length
      if (figureArtifacts.length > 0) {
        finalStatePatch.plotlyFigure = figureArtifacts[0]?.data
        applyConversationResultState(requestConversationId, finalStatePatch, { hasFigures: true })
      } else if (dataframeArtifacts.length > 0) {
        finalStatePatch.resultData = dataframeArtifacts[0].data
        applyConversationResultState(requestConversationId, finalStatePatch, { hasDataframes: true })
      } else if (scalarArtifacts.length > 0 || inlineScalarResult) {
        applyConversationResultState(requestConversationId, finalStatePatch)
      } else if (artifactItems.length > 0) {
        applyConversationResultState(requestConversationId, finalStatePatch)
      }
    } else {
      if (inlineScalarResult) {
        finalStatePatch.scalars = [inlineScalarResult]
        applyConversationResultState(requestConversationId, finalStatePatch)
      } else if (Object.keys(finalStatePatch).length > 0) {
        applyConversationResultState(requestConversationId, finalStatePatch)
      }
    }
    if (
      responseTurnId
      && requestConversationId === String(conversationStore.activeConversationId || '').trim()
    ) {
      artifactStore.requestActiveTurnArtifactRefresh()
    }

    setTimeout(() => {
      const scrollableContainer = document.querySelector('[data-chat-scroll-container]')
      if (scrollableContainer) {
        scrollableContainer.scrollTop = scrollableContainer.scrollHeight
      }
    }, 200)

  } catch (error: any) {
    console.error('Analysis failed:', error)

    if (warningTimer) clearTimeout(warningTimer)
    if (cancelTimer) clearTimeout(cancelTimer)

    let errorTitle = 'Analysis Failed'
    let errorMessage = 'Failed to generate code. Please try again.'
    const status = Number(error?.response?.status ?? error?.status ?? 0)
    const backendDetail = extractApiErrorMessage(error, '')

    if (error.name === 'AbortError' || signal.aborted) {
      if (runControl.wasStopped(requestConversationId)) {
        errorTitle = 'Generation Stopped'
        errorMessage = 'Response generation was stopped.'
        operationStatus = 'failed'
        operationMessage = errorMessage
        conversationStore.markLastMessageStreamStopped(errorMessage, localMessageId, { conversationId: requestConversationId })
        toast.error(errorTitle, errorMessage)
        return
      } else {
        errorTitle = 'Request Cancelled'
        errorMessage = 'Your query was cancelled due to timeout.'
      }
    } else if (status === 400) {
      errorTitle = 'Invalid Request'
      errorMessage = backendDetail || 'The request is invalid. Please review your dataset and schema setup.'
    } else if (status === 401) {
      errorTitle = 'Authentication Error'
      errorMessage = backendDetail || 'Please check your API key and try again.'
    } else if (status === 403) {
      errorTitle = 'Access Denied'
      errorMessage = backendDetail || 'You do not have permission to perform this action.'
    } else if (status === 429) {
      errorTitle = 'Rate Limit Exceeded'
      errorMessage = backendDetail || 'Too many requests. Please wait a moment and try again.'
    } else if (status >= 500) {
      errorTitle = 'Backend Error'
      errorMessage = backendDetail || 'The server encountered an error. Please try again later.'
    } else if (error.code === 'NETWORK_ERROR' || !navigator.onLine) {
      errorTitle = 'Network Error'
      errorMessage = 'Unable to connect to the server. Please check your internet connection.'
    } else if (backendDetail) {
      errorMessage = backendDetail
    }

    operationStatus = 'failed'
    operationMessage = errorMessage
    toast.error(
      errorTitle,
      errorMessage,
      7000,
      {
        source: status > 0 ? 'Backend' : 'Frontend',
        statusCode: status || null,
        category: 'llm_api',
      },
    )
    applyConversationResultState(requestConversationId, { terminalOutput: `Error: ${errorMessage}` })
    conversationStore.updateLastMessageExplanation(errorMessage, localMessageId, { conversationId: requestConversationId })
    if (attachmentsPayload.length > 0) {
      pendingAttachments.value = attachmentsPayload.map((item) => ({
        ...item,
        preview_url: `data:${item.media_type};base64,${item.data_base64}`,
        size: 0,
      }))
    }
  } finally {
    if (warningTimer) clearTimeout(warningTimer)
    if (cancelTimer) clearTimeout(cancelTimer)
    await refreshRuntimeStatusAfterExplicitWork(workspaceStore.activeWorkspaceId)
    runControl.clearStopped(requestConversationId)
    executionStore.setConversationRun(requestConversationId, null)
    executionStore.finishBackgroundOperation(operationId, {
      status: operationStatus,
      title: operationStatus === 'failed' ? 'Chat response failed' : 'Chat response complete',
      message: operationMessage,
    })
  }
}

function handleNewLine(event: any) {
  const textarea = event.target
  const start = textarea.selectionStart
  const end = textarea.selectionEnd

  question.value = question.value.substring(0, start) + '\n' + question.value.substring(end)

  setTimeout(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  }, 0)
}

onMounted(() => {
  initializeVoiceInput()
  window.addEventListener('resize', updateSuggestionPlacement)
})

onUnmounted(() => {
  if (isVoiceInputActive.value) {
    stopVoiceInput()
  }
  window.removeEventListener('resize', updateSuggestionPlacement)
})

watch(() => workspaceStore.activeWorkspaceId, () => {
  clearSuggestions()
})

watch(() => conversationStore.currentQuestion, async (nextQuestion) => {
  const prompt = String(nextQuestion || '').trim()
  if (!prompt || prompt === question.value.trim()) return

  const messages = Array.isArray(conversationStore.chatHistory) ? conversationStore.chatHistory : []
  const latestSubmittedQuestion = String(messages[messages.length - 1]?.question || '').trim()
  if (latestSubmittedQuestion === prompt) return

  question.value = prompt
  questionHistoryIndex.value = -1
  questionHistoryDraft.value = ''
  clearSuggestions()
  await nextTick()
  if (textareaRef.value) {
    textareaRef.value.focus()
    const caret = question.value.length
    textareaRef.value.selectionStart = caret
    textareaRef.value.selectionEnd = caret
  }
  void updateAutocompleteSuggestions()
})

watch(() => workspaceStore.columnCatalog, () => {
  void updateAutocompleteSuggestions()
}, { deep: true })
</script>

<style scoped>
.voice-input-pulse {
  animation: voice-pulse 1.4s infinite ease-in-out;
  background-color: var(--color-accent) !important;
  color: var(--color-on-accent) !important;
}

@keyframes voice-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--color-accent) 65%, transparent);
  }
  50% {
    box-shadow: 0 0 0 8px color-mix(in srgb, var(--color-accent) 0%, transparent);
  }
}
</style>
