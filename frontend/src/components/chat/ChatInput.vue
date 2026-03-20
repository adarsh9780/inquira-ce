<template>
  <div class="space-y-2">
    <!-- Main Input Card (Cursor-style) -->
    <div class="relative">
      <div
        ref="inputCardRef"
        class="relative flex flex-col rounded-2xl border transition-all duration-150"
        @dragenter.prevent="handleAttachmentDragEnter"
        @dragover.prevent="handleAttachmentDragOver"
        @dragleave.prevent="handleAttachmentDragLeave"
        @drop.prevent="handleAttachmentDrop"
        style="
          background-color: var(--color-base);
          border-color: var(--color-border);
          box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        "
        :style="composerCardStyle"
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
        @focus="isFocused = true"
        @blur="isFocused = false"
        placeholder="How can I help you today?"
        class="w-full px-4 pt-4 pb-2 resize-none focus:outline-none text-sm leading-relaxed bg-transparent border-none"
        style="color: var(--color-text-main); min-height: 72px;"
        :class="{ 'opacity-60 cursor-not-allowed': !appStore.canAnalyze || appStore.isLoading }"
        :disabled="!appStore.canAnalyze || appStore.isLoading"
      />

      <div v-if="pendingAttachments.length" class="px-4 pb-2">
        <div class="flex flex-wrap gap-2">
          <div
            v-for="attachment in pendingAttachments"
            :key="attachment.attachment_id"
            class="group/attachment flex items-center gap-2 rounded-xl border px-2 py-2"
            style="border-color: var(--color-border); background-color: color-mix(in srgb, var(--color-surface) 75%, transparent);"
          >
            <img
              :src="attachment.preview_url"
              :alt="attachment.filename"
              class="h-12 w-12 rounded-lg object-cover"
            />
            <div class="min-w-0">
              <p class="max-w-[150px] truncate text-xs font-medium" style="color: var(--color-text-main);">{{ attachment.filename }}</p>
              <p class="text-[11px]" style="color: var(--color-text-muted);">{{ formatAttachmentSize(attachment.size) }}</p>
            </div>
            <button
              type="button"
              class="btn-icon opacity-70 transition-opacity group-hover/attachment:opacity-100"
              title="Remove image"
              @click="removePendingAttachment(attachment.attachment_id)"
            >
              <XMarkIcon class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

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

      <!-- Bottom Action Row -->
      <div class="flex items-center justify-between px-3 pb-3 pt-1">

        <!-- Left: Add button -->
        <button
          type="button"
          class="btn-icon"
          title="Attach images"
          @click="openAttachmentPicker"
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
            @click="handleActionButtonClick"
            :disabled="!canTriggerActionButton"
            class="w-6 h-6 flex items-center justify-center transition-all duration-150 focus:outline-none"
            :class="
              canTriggerActionButton
                ? 'text-zinc-900 hover:text-zinc-700'
                : 'cursor-default opacity-50'
            "
            :title="actionButtonTitle"
          >
            <StopCircleIcon v-if="appStore.isLoading" class="w-6 h-6" />
            <span
              v-else-if="isVoiceInputActive"
              class="flex w-6 h-6 items-center justify-center rounded-full bg-zinc-900 text-white animate-pulse"
            >
              <MicrophoneIcon class="w-3 h-3" />
            </span>
            <span
              v-else-if="isComposerEmpty"
              class="flex w-6 h-6 items-center justify-center rounded-full bg-zinc-900 text-white"
            >
              <MicrophoneIcon class="w-3 h-3" />
            </span>
            <ArrowUpCircleIcon v-else class="w-6 h-6" />
          </button>
        </div>

      </div>
      </div>

      <div
        v-if="showCommandSuggestions"
        class="absolute left-0 right-0 z-[70] overflow-hidden rounded-xl border shadow-lg"
        :class="suggestionsOpenUp ? 'bottom-full mb-2' : 'top-full mt-1'"
        style="background-color: var(--color-base); border-color: var(--color-border);"
      >
        <ul class="py-1">
          <li v-for="(item, index) in commandSuggestions" :key="item.name">
            <button
              type="button"
              class="flex w-full items-start justify-between gap-3 px-3 py-2 text-left text-sm transition-colors"
              :class="index === selectedCommandIndex ? 'bg-black/[0.05]' : 'hover:bg-black/[0.03]'"
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

      <ColumnSuggest
        v-if="showColumnSuggestions"
        :items="columnSuggestions"
        :selected-index="selectedColumnIndex"
        :open-up="suggestionsOpenUp"
        @select="acceptColumnSuggestion"
      />
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import executionService from '../../services/executionService'
import { executeCommand, getRegisteredCommands, isCommand } from '../../services/commandRegistry'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { buildBrowserDataPath, inferTableNameFromDataPath } from '../../utils/chatBootstrap'
import { normalizePlotlyFigure } from '../../utils/figurePayload'
import { modelSupportsImages, SUPPORTED_CHAT_IMAGE_TYPES } from '../../utils/modelCapabilities'
import ModelSelector from '../ui/ModelSelector.vue'
import ColumnSuggest from './ColumnSuggest.vue'
import {
  PlusIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
  PhotoIcon,
} from '@heroicons/vue/24/outline'
import { ArrowUpCircleIcon, MicrophoneIcon, StopCircleIcon } from '@heroicons/vue/24/solid'

const appStore = useAppStore()

const question = ref('')
const isFocused = ref(false)
const textareaRef = ref(null)
const inputCardRef = ref(null)
const attachmentInputRef = ref(null)
const commandSuggestions = ref([])
const selectedCommandIndex = ref(0)
const columnSuggestions = ref([])
const selectedColumnIndex = ref(0)
const questionHistoryIndex = ref(-1)
const questionHistoryDraft = ref('')
const activeTokenRange = ref({ start: 0, end: 0, token: '' })
const suggestionsOpenUp = ref(false)
const pendingAttachments = ref([])
const isAttachmentDragActive = ref(false)
const dragDepth = ref(0)
const supportsVoiceInput = ref(false)
const isVoiceInputActive = ref(false)
const speechRecognition = ref(null)
const voiceDraftPrefix = ref('')
const activeAbortController = ref(null)
const userRequestedStop = ref(false)

const showCommandSuggestions = computed(() => commandSuggestions.value.length > 0)
const showColumnSuggestions = computed(() => columnSuggestions.value.length > 0)
const imageAttachmentsSupported = computed(() => modelSupportsImages(appStore.selectedModel))
const composerCardStyle = computed(() => {
  const style = isFocused.value
    ? {
      borderColor: 'var(--color-border-hover)',
      boxShadow: '0 0 0 3px color-mix(in srgb, var(--color-text-main) 5%, transparent)',
    }
    : {}
  if (isAttachmentDragActive.value) {
    return {
      ...style,
      borderColor: 'var(--color-border-hover)',
      boxShadow: '0 0 0 3px color-mix(in srgb, var(--color-border-hover) 18%, transparent)',
    }
  }
  return style
})

const canSend = computed(() =>
  appStore.canAnalyze &&
  (question.value.trim().length > 0 || pendingAttachments.value.length > 0) &&
  question.value.length <= 1000 &&
  !appStore.isLoading
)
const isComposerEmpty = computed(() =>
  question.value.trim().length === 0 && pendingAttachments.value.length === 0
)
const canTriggerVoiceInput = computed(() =>
  appStore.canAnalyze &&
  isComposerEmpty.value &&
  supportsVoiceInput.value &&
  !appStore.isLoading
)
const canTriggerActionButton = computed(() => {
  if (appStore.isLoading) return true
  if (!appStore.canAnalyze) return false
  if (canSend.value) return true
  return isComposerEmpty.value && supportsVoiceInput.value
})
const actionButtonTitle = computed(() => {
  if (appStore.isLoading) return 'Stop generation'
  if (canSend.value) return 'Send (Enter)'
  if (canTriggerVoiceInput.value) {
    return isVoiceInputActive.value ? 'Stop voice input' : 'Start voice input'
  }
  if (isComposerEmpty.value) {
    return 'Voice input unavailable on this device/browser'
  }
  return 'Type a message or attach images to send'
})

const FINAL_STREAM_NODES = new Set([
  'explain_code',
  'noncode_generator',
  'general_purpose',
  'unsafe_rejector',
  'finalize',
  'chat',
  'reject'
])

function extractLangGraphTokenText(payload) {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) {
    for (const item of payload) {
      const nested = extractLangGraphTokenText(item)
      if (nested) return nested
    }
    return ''
  }
  if (typeof payload === 'object') {
    if (typeof payload.text === 'string' && payload.text) return payload.text
    if (typeof payload.content === 'string' && payload.content) return payload.content
    const content = payload.content
    if (Array.isArray(content)) {
      for (const item of content) {
        if (item && typeof item === 'object' && item.type === 'text' && typeof item.text === 'string') {
          if (item.text) return item.text
        }
      }
    }
  }
  return ''
}

function parseArtifactTimestampMs(value) {
  const raw = String(value || '').trim()
  if (!raw) return 0
  const parsed = Date.parse(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

function sortArtifactsNewestFirst(items) {
  if (!Array.isArray(items)) return []
  return [...items].sort((left, right) => {
    const delta = parseArtifactTimestampMs(right?.created_at) - parseArtifactTimestampMs(left?.created_at)
    if (delta !== 0) return delta
    return String(right?.artifact_id || '').localeCompare(String(left?.artifact_id || ''))
  })
}

function formatAttachmentSize(size) {
  const bytes = Number(size || 0)
  if (!Number.isFinite(bytes) || bytes <= 0) return 'Image'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function buildAttachmentId(file) {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${String(file?.name || 'image')}`
}

function openAttachmentPicker() {
  if (!imageAttachmentsSupported.value) {
    toast.error('Images Not Supported', 'The selected model does not support image attachments.')
    return
  }
  attachmentInputRef.value?.click()
}

async function fileToBase64(file) {
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

async function appendPendingAttachments(files) {
  if (!imageAttachmentsSupported.value) {
    toast.error('Images Not Supported', 'Switch to a vision-capable model before attaching images.')
    return
  }
  const normalizedFiles = Array.from(files || []).filter((file) => SUPPORTED_CHAT_IMAGE_TYPES.has(String(file?.type || '').toLowerCase()))
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

async function handleAttachmentSelection(event) {
  try {
    await appendPendingAttachments(event?.target?.files || [])
  } catch (error) {
    toast.error('Image Attach Failed', extractApiErrorMessage(error, 'Failed to attach image.'))
  } finally {
    if (event?.target) event.target.value = ''
  }
}

function removePendingAttachment(attachmentId) {
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

async function handleAttachmentDrop(event) {
  dragDepth.value = 0
  isAttachmentDragActive.value = false
  try {
    await appendPendingAttachments(event?.dataTransfer?.files || [])
  } catch (error) {
    toast.error('Image Attach Failed', extractApiErrorMessage(error, 'Failed to attach image.'))
  }
}

function handleModelChange(model) {
  appStore.setSelectedModel(model)
}

function initializeVoiceInput() {
  if (typeof window === 'undefined') return
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
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
    recognition.onerror = (event) => {
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
    recognition.onresult = (event) => {
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
  userRequestedStop.value = true
  activeAbortController.value?.abort()
}

function handleActionButtonClick() {
  if (appStore.isLoading) {
    handleStopGeneration()
    return
  }
  if (canSend.value) {
    void handleSubmit()
    return
  }
  if (canTriggerVoiceInput.value) {
    if (isVoiceInputActive.value) {
      stopVoiceInput()
    } else {
      startVoiceInput()
    }
  }
}

function isSimpleIdentifier(value) {
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(String(value || '').trim())
}

function quoteSqlIdentifier(value) {
  return `"${String(value || '').replace(/"/g, '""')}"`
}

function buildColumnReference(tableName, columnName) {
  const table = String(tableName || '').trim()
  const column = String(columnName || '').trim()
  if (!table || !column) return ''
  if (isSimpleIdentifier(column)) {
    return `${table}.${column}`
  }
  return `${table}.${quoteSqlIdentifier(column)}`
}

function buildColumnSuggestion(item) {
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
  const merged = []
  const seen = new Set()

  const addCandidate = (tableName, columnName, dtype = '') => {
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

  const catalogItems = Array.isArray(appStore.columnCatalog) ? appStore.columnCatalog : []
  catalogItems.forEach((item) => {
    addCandidate(item?.table_name, item?.column_name, item?.dtype)
  })

  const activeTable = String(appStore.ingestedTableName || '').trim()
  const ingestedItems = Array.isArray(appStore.ingestedColumns) ? appStore.ingestedColumns : []
  ingestedItems.forEach((item) => {
    addCandidate(
      activeTable,
      item?.name || item?.column_name,
      item?.dtype || item?.type || ''
    )
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

function tokenRangeAtCursor(text, cursor) {
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

function applyTokenReplacement(replacement, { appendSpace = false } = {}) {
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

function acceptCommandSuggestion(item = null) {
  const selected = item || commandSuggestions.value[selectedCommandIndex.value]
  if (!selected) return
  applyTokenReplacement(`/${selected.name}`, { appendSpace: true })
  clearSuggestions()
}

function acceptColumnSuggestion(item = null) {
  const selected = item || columnSuggestions.value[selectedColumnIndex.value]
  if (!selected) return
  applyTokenReplacement(String(selected.insertText || `${selected.table_name}.${selected.column_name}`))
  clearSuggestions()
}

function navigateSuggestion(step) {
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

  if (!Array.isArray(appStore.columnCatalog) || appStore.columnCatalog.length === 0) {
    await appStore.fetchColumnCatalog()
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

function handleCaretInteraction(event = null) {
  if (
    event &&
    SUGGESTION_NAVIGATION_KEYS.has(String(event.key || '')) &&
    (showCommandSuggestions.value || showColumnSuggestions.value)
  ) {
    return
  }
  void updateAutocompleteSuggestions()
}

function setQuestionFromHistory(value) {
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

function isHistoryNavigationAllowed(event, step) {
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

function navigateQuestionHistory(step) {
  const history = Array.isArray(appStore.questionHistory) ? appStore.questionHistory : []
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

function handleKeydown(event) {
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
    clearSuggestions()
    return
  }
  if ((showCommandSuggestions.value || showColumnSuggestions.value) && event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (showCommandSuggestions.value) {
      acceptCommandSuggestion()
    } else {
      acceptColumnSuggestion()
    }
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

function applyCommandResultToStore(commandResult) {
  const payload = commandResult?.result && typeof commandResult.result === 'object'
    ? commandResult.result
    : null
  const columns = Array.isArray(payload?.columns) ? payload.columns.map((col) => String(col)) : []
  const rows = Array.isArray(payload?.data) ? payload.data : []
  const hasTablePayload = columns.length > 0

  if (hasTablePayload) {
    const tableResult = {
      columns,
      data: rows,
      row_count: Number.isFinite(Number(payload?.row_count)) ? Number(payload.row_count) : rows.length,
      result_type: String(payload?.result_type || commandResult?.result_type || 'table'),
    }
    appStore.setDataframes([
      {
        name: String(commandResult?.name || 'command_result'),
        data: tableResult,
      },
    ])
    appStore.setResultData(tableResult)
    appStore.setFigures([])
    appStore.setPlotlyFigure(null)
    appStore.setDataPane('table')
    appStore.setActiveTab('table')
  } else {
    appStore.setDataframes([])
    appStore.setResultData(null)
    appStore.setFigures([])
    appStore.setPlotlyFigure(null)
    appStore.setDataPane('output')
    appStore.setActiveTab('output')
  }

  const output = String(commandResult?.output || `/${commandResult?.name || 'command'} executed.`)
  appStore.setTerminalOutput(output)
  appStore.appendTerminalEntry({
    kind: 'output',
    source: 'analysis',
    label: `/${String(commandResult?.name || 'command')}`,
    status: 'success',
    stdout: output,
    stderr: '',
    exitCode: 0,
  })
}

async function handleSlashCommand(questionText) {
  appStore.setLoading(true)
  let commandMessageCreated = false
  try {
    const workspaceId = appStore.activeWorkspaceId
    if (!workspaceId) {
      throw new Error('Create/select a workspace before analysis.')
    }

    appStore.addChatMessage(questionText, 'Running command...')
    commandMessageCreated = true
    await ensureWorkspaceDatasetReady(workspaceId)
    const result = await executeCommand(questionText, { appStore, apiService, executionService })
    const persistedConversationId = String(result?.conversation_id || '').trim()
    if (persistedConversationId && persistedConversationId !== String(appStore.activeConversationId || '').trim()) {
      appStore.setActiveConversationId(persistedConversationId)
    }
    if (persistedConversationId) {
      await appStore.fetchConversations()
    }
    appStore.updateLastMessageExplanation(
      String(result?.output || `/${String(result?.name || 'command')} executed.`)
    )
    applyCommandResultToStore(result)
  } catch (error) {
    const message = extractApiErrorMessage(error, 'Failed to run command.')
    if (commandMessageCreated) {
      appStore.updateLastMessageExplanation(`Command failed: ${message}`)
    }
    toast.error('Command Failed', message)
    appStore.setTerminalOutput(`Error: ${message}`)
    appStore.appendTerminalEntry({
      kind: 'output',
      source: 'analysis',
      label: 'Command error',
      status: 'error',
      stdout: '',
      stderr: message,
      exitCode: 1,
    })
    appStore.setDataPane('output')
    appStore.setActiveTab('output')
  } finally {
    appStore.setLoading(false)
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
    appStore.addQuestionHistoryEntry(questionText)
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

  appStore.addChatMessage(questionText, '', { attachments: attachmentsPayload })
  appStore.setLoading(true)

  const abortController = new AbortController()
  activeAbortController.value = abortController
  userRequestedStop.value = false
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
    response = await apiService.v1AnalyzeStream(
      {
        workspace_id: workspaceId,
        conversation_id: appStore.activeConversationId || null,
        question: questionText,
        current_code: appStore.pythonFileContent || '',
        model: appStore.selectedModel,
        context: appStore.schemaContext.trim() || null,
        table_name: null,
        preferred_table_name: schemaPayload.tableName,
        active_schema: schemaPayload.activeSchema,
        attachments: attachmentsPayload,
        api_key: null
      },
      {
        signal,
        onEvent: (evt) => {
          if ((evt.event === 'messages' || evt.event === 'messages/partial' || evt.event === 'messages-tuple')) {
            const text = extractLangGraphTokenText(evt.data)
            if (text) {
              appStore.appendLastMessageExplanationChunk(text)
            }
            return
          }
          if (evt.event === 'updates' && evt.data && typeof evt.data === 'object') {
            Object.entries(evt.data).forEach(([node, output]) => {
              const normalizedNode = String(node || '')
              const payload = (output && typeof output === 'object') ? output : {}
              appStore.appendLastMessageTraceEvent({
                type: 'node',
                node: normalizedNode,
                message: `${normalizedNode} completed`,
                output: String(payload.plan || payload.answer || payload.code || payload.current_code || '')
              })
            })
            return
          }
          if (evt.event === 'token' && typeof evt.data?.text === 'string') {
            const nodeName = String(evt.data?.node || '').trim().toLowerCase()
            if (FINAL_STREAM_NODES.has(nodeName)) {
              appStore.appendLastMessageExplanationChunk(evt.data.text)
            } else {
              appStore.appendLastMessagePlanChunk(evt.data.text, evt.data.node || '')
            }
            return
          }
          if (evt.event === 'status' && evt.data?.message) {
            appStore.appendLastMessageTraceEvent({
              type: 'status',
              stage: evt.data?.stage || '',
              message: evt.data.message,
              output: evt.data?.output || ''
            })
            return
          }
          if (evt.event === 'node' && evt.data?.node) {
            appStore.appendLastMessageTraceEvent({
              type: 'node',
              node: evt.data.node,
              message: evt.data.message || '',
              output: evt.data?.output || ''
            })
            return
          }
          if (evt.event === 'agent_status' && evt.data?.message) {
            appStore.appendLastMessageTraceEvent({
              type: 'status',
              node: 'agent_status',
              stage: evt.data.step || '',
              message: evt.data.message,
              output: evt.data?.detail || evt.data?.output || ''
            })
            return
          }
          if (evt.event === 'tool_call' && evt.data?.call_id) {
            appStore.appendLastMessageToolCall(evt.data)
            return
          }
          if (evt.event === 'tool_progress' && evt.data?.call_id) {
            appStore.appendLastMessageToolProgress(evt.data)
            return
          }
          if (evt.event === 'tool_result' && evt.data?.call_id) {
            appStore.appendLastMessageToolResult(evt.data)
            return
          }
          if (evt.event === 'intervention_request' && evt.data?.id) {
            appStore.setLastMessageInterventionRequest(evt.data)
            return
          }
          if (evt.event === 'intervention_response' && evt.data?.id) {
            appStore.setLastMessageInterventionResponse(evt.data)
          }
        }
      }
    )

    if (response?.conversation_id && response.conversation_id !== appStore.activeConversationId) {
      appStore.setActiveConversationId(response.conversation_id)
      await appStore.fetchConversations()
    }

    const { is_safe, code, current_code, explanation, result_explanation, code_explanation } = response
    const finalCode = (code ?? current_code ?? '').toString()
    appStore.setLastMessageAnalysisMetadata(response?.metadata || {})
    const finalExplanation = (result_explanation ?? explanation ?? '').toString()
    appStore.setLastMessageCodeSnapshot(finalCode)
    appStore.setLastMessageCodeExplanation((code_explanation ?? '').toString())

    if (!is_safe) {
      appStore.updateLastMessageExplanation(finalExplanation || 'Your query was flagged as potentially unsafe.')
      return
    }

    appStore.updateLastMessageExplanation(finalExplanation)
    appStore.setGeneratedCode(finalCode)
    if (finalCode.trim()) {
      appStore.setPythonFileContent(finalCode)
    }

    const previousDataPane = String(appStore.dataPane || '').trim().toLowerCase()
    if (finalCode && finalCode.trim()) {
      const executionStderr = response?.execution?.stderr || ''
      const executionStdout = response?.execution?.stdout || ''
      appStore.setTerminalOutput(executionStderr || executionStdout || response.stdout || response.terminal_output || 'Code generated and executed.')

      const inlineFigure = normalizePlotlyFigure(response.plotly_figure || response.result)
      if (inlineFigure) {
        appStore.setPlotlyFigure(inlineFigure)
        appStore.setResultData(null)
        appStore.setDataPane('figure')
      } else if (response.result?.columns && response.result?.data) {
        appStore.setResultData(response.result)
        appStore.setPlotlyFigure(null)
        appStore.setDataPane('table')
      }
    }

    const artifactItems = sortArtifactsNewestFirst(Array.isArray(response?.artifacts) ? response.artifacts : [])
    if (artifactItems.length > 0) {
      const dataframeArtifacts = artifactItems
        .filter((item) => String(item?.kind || '') === 'dataframe')
        .map((item) => ({
          name: String(item?.logical_name || 'dataframe'),
          data: {
            artifact_id: item?.artifact_id,
            row_count: Number(item?.row_count || 0),
            columns: Array.isArray(item?.schema) ? item.schema.map((col) => String(col?.name || '')) : [],
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
            name: String(item?.logical_name || 'figure'),
            artifact_id: item?.artifact_id || null,
            created_at: String(item?.created_at || ''),
            data: figure,
          }
        })
        .filter(Boolean)

      appStore.setDataframes(dataframeArtifacts)
      appStore.setFigures(figureArtifacts)
      if (previousDataPane === 'table' && dataframeArtifacts.length > 0) {
        appStore.setResultData(dataframeArtifacts[0].data)
        appStore.setDataPane('table')
      } else if (previousDataPane === 'figure' && figureArtifacts.length > 0) {
        appStore.setPlotlyFigure(figureArtifacts[0].data)
        appStore.setDataPane('figure')
      } else if (dataframeArtifacts.length > 0) {
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
    const status = Number(error?.response?.status ?? error?.status ?? 0)

    if (error.name === 'AbortError' || signal.aborted) {
      if (userRequestedStop.value) {
        errorTitle = 'Generation Stopped'
        errorMessage = 'Response generation was stopped.'
      } else {
        errorTitle = 'Request Cancelled'
        errorMessage = 'Your query was cancelled due to timeout.'
      }
    } else if (status === 400) {
      errorTitle = 'Invalid Request'
      errorMessage = extractApiErrorMessage(error, 'The request is invalid. Please review your dataset and schema setup.')
    } else if (status === 401) {
      errorTitle = 'Authentication Error'
      errorMessage = 'Please check your API key and try again.'
    } else if (status === 403) {
      errorTitle = 'Access Denied'
      errorMessage = 'You do not have permission to perform this action.'
    } else if (status === 429) {
      errorTitle = 'Rate Limit Exceeded'
      errorMessage = 'Too many requests. Please wait a moment and try again.'
    } else if (status >= 500) {
      errorTitle = 'Server Error'
      errorMessage = 'The server encountered an error. Please try again later.'
    } else if (error.code === 'NETWORK_ERROR' || !navigator.onLine) {
      errorTitle = 'Network Error'
      errorMessage = 'Unable to connect to the server. Please check your internet connection.'
    }

    toast.error(errorTitle, errorMessage)
    appStore.setTerminalOutput(`Error: ${errorMessage}`)
    appStore.updateLastMessageExplanation(errorMessage)
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
    activeAbortController.value = null
    userRequestedStop.value = false
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

onMounted(() => {
  initializeVoiceInput()
  if (appStore.activeWorkspaceId) {
    void appStore.fetchColumnCatalog({ force: true })
  }
  window.addEventListener('resize', updateSuggestionPlacement)
})

onUnmounted(() => {
  if (isVoiceInputActive.value) {
    stopVoiceInput()
  }
  window.removeEventListener('resize', updateSuggestionPlacement)
})

watch(() => appStore.activeWorkspaceId, () => {
  clearSuggestions()
  if (appStore.activeWorkspaceId) {
    void appStore.fetchColumnCatalog({ force: true })
  }
})

watch(() => appStore.ingestedTableName, () => {
  void updateAutocompleteSuggestions()
})

watch(() => appStore.ingestedColumns, () => {
  void updateAutocompleteSuggestions()
}, { deep: true })
</script>
