<template>
  <div ref="chatContainer" class="space-y-4" style="min-height: 200px;" role="log" aria-live="polite" aria-relevant="additions" :aria-busy="executionStore.isConversationRunning(conversationStore.activeConversationId)">
    <!-- Loading indicator for first message when no history yet -->
    <div v-if="executionStore.isConversationRunning(conversationStore.activeConversationId) && displayedChatHistory.length === 0" role="status" aria-live="polite" class="flex items-center justify-center py-6">
      <div class="analyzing-status">
        <div class="analyzing-spinner" aria-hidden="true"></div>
        <span class="analyzing-status-text">Analyzing your question...</span>
      </div>
    </div>

    <div
      v-for="message in displayedChatHistory"
      :key="message.id"
      class="group"
    >
      <!-- User Message -->
      <ChatUserMessage>
        <div class="user-turn-bubble px-3 py-2.5 rounded-2xl rounded-tl-sm">
          <div v-if="message.attachments && message.attachments.length" class="mb-3 grid grid-cols-2 gap-2">
            <img
              v-for="attachment in message.attachments"
              :key="attachment.attachment_id || attachment.filename"
              :src="attachmentPreviewSrc(attachment)"
              :alt="attachment.filename || 'Attached image'"
              class="w-full max-h-48 rounded-xl object-cover border"
              style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent);"
            />
          </div>
          <p
            class="chat-question-text text-[14px] font-medium whitespace-pre-wrap leading-[1.7]"
            style="color: var(--color-text-main);"
            v-html="renderQuestionWithHighlights(message.question)"
          ></p>
        </div>
        <div class="mt-1 px-1 flex items-center gap-1.5">
          <span class="text-[12px] font-normal leading-[1.3]" style="color: var(--color-text-muted);">{{ formatTimestamp(message.timestamp) }}</span>
          <button
            @click.stop="copyQuestion(message)"
            type="button"
            aria-label="Copy question"
            class="transition-opacity text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] inline-flex items-center"
            :class="copiedUserMessageId === message.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100'"
            title="Copy question"
          >
            <span v-if="copiedUserMessageId === message.id" class="text-[12px] font-medium text-[var(--color-success)]">Copied</span>
            <DocumentDuplicateIcon v-else class="h-3 w-3" />
          </button>
        </div>
      </ChatUserMessage>

      <!-- Assistant Response -->
      <ChatAssistantMessage v-if="hasAssistantContent(message)">
        <div class="px-3 py-2.5 rounded-2xl rounded-tl-sm" style="background-color: transparent">
          <div v-if="message.explanation" class="chat-markdown-content final-response-body max-w-none" style="color: var(--color-text-main);">
            <MarkdownContent :content="message.explanation" />
          </div>

          <div
            v-if="hasAnalysisDetails(message)"
            class="mt-3 view-code-details"
            :class="isAnalysisDetailsOpen(message) ? 'view-code-details-open' : ''"
          >
            <button
              type="button"
              class="view-code-toggle"
              :aria-expanded="isAnalysisDetailsOpen(message)"
              @click="toggleAnalysisDetails(message)"
            >
              <span class="inline-flex items-center gap-1.5">
                <CodeBracketIcon class="h-4 w-4" aria-hidden="true" />
                <span>{{ isMessageRunning(message) ? 'Working' : 'Analysis details' }}</span>
                <span v-if="isMessageRunning(message)" class="live-progress-dot" aria-hidden="true"></span>
                <span class="view-code-caret" aria-hidden="true">↓</span>
              </span>
            </button>
            <div
              class="motion-disclosure"
              :class="isAnalysisDetailsOpen(message) ? 'motion-disclosure-open' : ''"
              :aria-hidden="!isAnalysisDetailsOpen(message)"
            >
            <div class="motion-disclosure-content">
            <div class="view-code-panel">
              <div v-if="isMessageRunning(message)" class="live-progress-status" role="status" aria-live="polite">
                <div class="analyzing-spinner" aria-hidden="true"></div>
                <div class="min-w-0">
                  <p class="live-progress-action">{{ currentProgress(message).action }}</p>
                  <p v-if="currentProgress(message).detail" class="live-progress-detail">{{ currentProgress(message).detail }}</p>
                </div>
              </div>

              <div v-if="reasoningRows(message).length" class="stream-reasoning-list">
                <div v-for="row in reasoningRows(message)" :key="row.id" class="stream-reasoning-item">
                  <template v-if="row.sections?.length">
                    <div v-for="section in row.sections" :key="`${row.id}-${section.label}`" class="stream-reasoning-section">
                      <p class="stream-reasoning-label">{{ section.label }}</p>
                      <p class="stream-reasoning-text">{{ section.text }}</p>
                    </div>
                  </template>
                  <template v-else>
                    <p class="stream-reasoning-label">Reasoning</p>
                    <p class="stream-reasoning-text">{{ row.message }}</p>
                  </template>
                </div>
              </div>

              <div v-if="hasActionProgress(message)" class="stream-action-section">
                <div v-if="SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length" class="ephemeral-trace-list">
                  <div v-for="row in ephemeralRows(message)" :key="row.id" class="ephemeral-trace-item">
                    <p class="ephemeral-trace-action">{{ row.action }}</p>
                    <p v-if="row.detail" class="ephemeral-trace-detail">{{ row.detail }}</p>
                  </div>
                </div>

                <div v-if="toolActivityRows(message).length" class="space-y-4">
                  <ToolActivityCard
                    v-for="(activity, index) in toolActivityRows(message)"
                    :key="activity.call_id || activity.started_at"
                    :activity="activity"
                    :collapsed="isToolActivityOutputCollapsed(message, index)"
                  />
                </div>
              </div>

              <div v-if="tableUsageSummary(message)" class="mb-3">
                <span class="view-code-meta-badge">{{ tableUsageSummary(message) }}</span>
              </div>
              <div
                v-if="message.codeExplanation"
                class="chat-markdown-content text-[14px] leading-[1.7] max-w-none mb-3"
                style="color: var(--color-text-main);"
              >
                <MarkdownContent :content="message.codeExplanation" />
              </div>
              <div v-if="shouldRenderCodeSnapshot(message)" class="chat-code-block">
                <div class="chat-code-header">
                  <span>python</span>
                  <button
                    type="button"
                    class="text-[13px] font-medium underline-offset-2 hover:underline"
                    style="color: var(--color-text-sub);"
                    @click="openCodePane"
                  >
                    Open Code
                  </button>
                </div>
                <MarkdownContent :content="message.codeSnapshot" mode="code" />
              </div>
            </div>
            </div>
            </div>
          </div>

        </div>
        <div v-if="message.explanation" class="flex items-center justify-end mt-1 px-4">
          <div
            class="flex items-center space-x-2 transition-opacity"
            :class="copiedAssistantMessageId === message.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100'"
          >
            <button
              @click="copyExplanation(message)"
              type="button"
              aria-label="Copy explanation"
              class="text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] transition-colors inline-flex items-center"
              :class="copiedAssistantMessageId === message.id ? '' : 'btn-icon text-xs p-1'"
              title="Copy explanation"
            >
              <span v-if="copiedAssistantMessageId === message.id" class="text-[12px] font-medium text-[var(--color-success)] px-1">Copied</span>
              <DocumentDuplicateIcon v-else class="h-3 w-3" />
            </button>
          </div>
        </div>
      </ChatAssistantMessage>
    </div>

    <!-- Loading indicator when analyzing - shown below last message -->
    <div v-if="executionStore.isConversationRunning(conversationStore.activeConversationId) && displayedChatHistory.length > 0 && !hasAssistantContent(displayedChatHistory.at(-1))" role="status" aria-live="polite" class="flex items-center justify-center py-6">
      <div class="analyzing-status">
        <div class="analyzing-spinner" aria-hidden="true"></div>
        <span class="analyzing-status-text">Analyzing your question...</span>
      </div>
    </div>

    <Transition name="motion-popover">
    <div v-if="showScrollToBottomButton" class="motion-popover-surface motion-popover-from-bottom sticky bottom-3 z-20 flex justify-end pr-2 pointer-events-none">
      <button
        type="button"
        class="pointer-events-auto inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium shadow-sm transition-colors"
        style="border-color: var(--color-border); background-color: var(--color-surface); color: var(--color-text-main);"
        aria-label="Scroll to bottom"
        title="Scroll to bottom"
        @click="handleScrollToBottomClick"
      >
        <ChevronDownIcon class="h-3.5 w-3.5" aria-hidden="true" />
        <span>Latest</span>
      </button>
    </div>
    </Transition>

    <!-- Sentinel for auto-scroll -->
    <div ref="end" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted, computed, defineAsyncComponent } from 'vue'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import {
  DocumentDuplicateIcon,
  ChevronDownIcon,
  CodeBracketIcon,
} from '@heroicons/vue/24/outline'
import ToolActivityCard from './ToolActivityCard.vue'
import ChatAssistantMessage from './ChatAssistantMessage.vue'
import ChatUserMessage from './ChatUserMessage.vue'
import { toolOutputHasRenderableContent } from '../../utils/toolOutputPreview'
import { formatTimestamp } from '../../utils/dateUtils'
import { selectDisplayedChatHistory } from '../../utils/chatHistoryView'
import { toast } from '../../composables/useToast'
import { useChatScrollFollow } from '../../composables/useChatScrollFollow'

const MarkdownContent = defineAsyncComponent(() => import('./MarkdownContent.vue'))
const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
useChatScrollFollow()
const chatContainer = ref<any>(null)
const scrollHost = ref<any>(null)
const end = ref<any>(null)
const expandedAnalysisMessageIds = ref(new Set())
const collapsedLiveAnalysisMessageIds = ref(new Set())
const SHOW_EPHEMERAL_TRACE = true
const showScrollToBottomButton = ref(false)
let shouldAutoScroll = true
let mutationObserver: MutationObserver | null = null
let lastScrollTop = 0

function isMessageRunning(message: any) {
  if (!executionStore.isConversationRunning(conversationStore.activeConversationId)) return false
  const messageId = String(message?.id || '').trim()
  return Boolean(messageId && messageId === String(lastMessageId.value || '').trim())
}

function isAnalysisDetailsOpen(message: any) {
  const messageId = String(message?.id || '').trim()
  if (expandedAnalysisMessageIds.value.has(messageId)) return true
  return isMessageRunning(message) && !collapsedLiveAnalysisMessageIds.value.has(messageId)
}

function toggleAnalysisDetails(message: any) {
  const messageId = String(message?.id || '').trim()
  if (!messageId) return
  if (isMessageRunning(message) && !expandedAnalysisMessageIds.value.has(messageId)) {
    const nextCollapsed = new Set(collapsedLiveAnalysisMessageIds.value)
    if (nextCollapsed.has(messageId)) nextCollapsed.delete(messageId)
    else nextCollapsed.add(messageId)
    collapsedLiveAnalysisMessageIds.value = nextCollapsed
    return
  }
  const next = new Set(expandedAnalysisMessageIds.value)
  if (next.has(messageId)) next.delete(messageId)
  else next.add(messageId)
  expandedAnalysisMessageIds.value = next
}

const displayedChatHistory = computed(() => selectDisplayedChatHistory({
  localHistory: conversationStore.chatHistory,
  activeTurnId: conversationStore.activeTurnId,
  activeTurn: conversationStore.activeTurn,
  isRunning: executionStore.isConversationRunning(conversationStore.activeConversationId),
}))

const lastMessageId = computed(() => displayedChatHistory.value.at(-1)?.id)

const SCROLL_THRESHOLD_PX = 100
const SHOW_SCROLL_BUTTON_THRESHOLD_PX = 220
const QUESTION_REFERENCE_RE = /\b[A-Za-z_][A-Za-z0-9_]*\."(?:[^"]|"")+"|\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*/g

function attachmentPreviewSrc(attachment: any) {
  const mediaType = String(attachment?.media_type || 'image/png').trim()
  const dataBase64 = String(attachment?.data_base64 || '').trim()
  if (!dataBase64) return ''
  return `data:${mediaType};base64,${dataBase64}`
}

function tableUsageSummary(message: any) {
  const metadata = message?.analysisMetadata
  if (!metadata || typeof metadata !== 'object') return ''
  const tables = Array.isArray(metadata.tables_used)
    ? metadata.tables_used.map((item: any) => String(item || '').trim()).filter(Boolean)
    : []
  if (tables.length === 0) return ''
  const joinsUsed = Boolean(metadata.joins_used)
  const joinKeys = Array.isArray(metadata.join_keys)
    ? metadata.join_keys.map((item: any) => String(item || '').trim()).filter(Boolean)
    : []
  if (!joinsUsed) {
    return `Tables used: ${tables.join(', ')}`
  }
  if (joinKeys.length > 0) {
    return `Tables used: ${tables.join(', ')} · Join keys: ${joinKeys.join(', ')}`
  }
  return `Tables used: ${tables.join(', ')} · Conservative join`
}


function escapeHtml(rawValue: any) {
  return String(rawValue || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderQuestionWithHighlights(question: any) {
  const text = String(question || '')
  if (!text) return ''
  const matcher = new RegExp(QUESTION_REFERENCE_RE.source, 'g')
  const matches = Array.from(text.matchAll(matcher))
  if (matches.length === 0) {
    return escapeHtml(text)
  }

  const parts = []
  let cursor = 0
  matches.forEach((match) => {
    const token = String(match?.[0] || '')
    const start = Number(match?.index || 0)
    const end = start + token.length
    if (!token || start < cursor) return
    parts.push(escapeHtml(text.slice(cursor, start)))
    parts.push(`<span class="chat-ref-highlight">${escapeHtml(token)}</span>`)
    cursor = end
  })
  parts.push(escapeHtml(text.slice(cursor)))
  return parts.join('')
}


const EPHEMERAL_LABELS: Record<string, string | null> = {
  check_safety: 'Checking if query is safe to process',
  check_relevancy: 'Checking if query matches your data',
  require_code: 'Determining whether code generation is needed',
  create_plan: 'Planning the analysis steps',
  agent_status: null // Use message from event payload directly
}
const HIDDEN_EPHEMERAL_NODES = new Set([
  'code_guard',
  'explain_code'
])

// Initialize shouldAutoScroll and setup listeners on mount
onMounted(() => {
  scrollHost.value = resolveScrollHost()
  shouldAutoScroll = true // Start with auto-scroll enabled
  showScrollToBottomButton.value = false

  // Listen for scroll events on the scrollable container
  const container = getScrollContainer()
  if (container) {
    lastScrollTop = container.scrollTop
    container.addEventListener('scroll', handleScroll, { passive: true })
    container.addEventListener('click', handleChatContainerClick)
  }

  // Setup MutationObserver for dynamic content
  if (chatContainer.value) {
    mutationObserver = new MutationObserver(() => {
      if (shouldAutoScroll) {
        scrollToBottom()
      }
    })
    mutationObserver.observe(chatContainer.value, { childList: true, subtree: true })
  }

  // Hydrated conversations mount with existing messages, so force initial bottom alignment.
  if (displayedChatHistory.value.length > 0) {
    nextTick(() => scrollToBottom())
    window.setTimeout(() => scrollToBottom({ behavior: 'auto', force: true, hardAlign: true }), 32)
  }
})

// Clean up event listener and observer when component unmounts
onUnmounted(() => {
  const container = getScrollContainer()
  if (container) {
    container.removeEventListener('scroll', handleScroll)
    container.removeEventListener('click', handleChatContainerClick)
  }
  if (mutationObserver) {
    mutationObserver.disconnect()
  }
})


const copiedUserMessageId = ref<any>(null)
const copiedAssistantMessageId = ref<any>(null)

async function copyQuestion(message: any) {
  if (!message) return
  try {
    await navigator.clipboard.writeText(message.question || '')
    copiedUserMessageId.value = message.id
    window.setTimeout(() => {
      if (copiedUserMessageId.value === message.id) {
        copiedUserMessageId.value = null
      }
    }, 3000)
  } catch (error: any) {
    console.error('Failed to copy question:', error)
    toast.error('Copy failed', 'Unable to copy question to clipboard')
  }
}

async function copyExplanation(message: any) {
  if (!message) return
  try {
    await navigator.clipboard.writeText(message.explanation || '')
    copiedAssistantMessageId.value = message.id
    window.setTimeout(() => {
      if (copiedAssistantMessageId.value === message.id) {
        copiedAssistantMessageId.value = null
      }
    }, 3000)
  } catch (error: any) {
    console.error('Failed to copy explanation:', error)
    toast.error('Copy failed', 'Unable to copy explanation to clipboard')
  }
}

function streamPlanText(message: any) {
  return String(message?.streamTrace?.planText || '').trim()
}

function streamTraceEvents(message: any) {
  const events = message?.streamTrace?.events
  return Array.isArray(events) ? events : []
}

function streamReasoningEvents(message: any) {
  const events = message?.streamTrace?.reasoning
  return Array.isArray(events) ? events : []
}

function streamToolCalls(message: any) {
  const calls = message?.streamTrace?.toolCalls
  return Array.isArray(calls) ? calls : []
}

function hasFinalResponse(message: any) {
  return Boolean(String(message?.explanation || '').trim())
}

function toolActivityRows(message: any) {
  return streamToolCalls(message).filter((activity) => String(activity?.tool || '').trim().toLowerCase() !== 'execute_python')
}

function isToolActivityOutputCollapsed(message: any, activityIndex: any) {
  const rows = toolActivityRows(message)
  const activity = rows[activityIndex]
  if (!toolOutputHasRenderableContent(activity)) return false
  if (String(message?.explanation || '').trim()) return true
  return rows
    .slice(activityIndex + 1)
    .some((nextActivity) => toolOutputHasRenderableContent(nextActivity))
}

function reasoningRows(message: any) {
  if (hasFinalResponse(message) && !isMessageRunning(message)) return []
  return streamReasoningEvents(message)
    .map((event, index) => ({
      id: `${message?.id || 'msg'}-reasoning-${String(event?.stage || 'intent')}-${index}`,
      message: normalizeEphemeralText(event?.message),
      sections: parseReasoningSections(event?.message),
    }))
    .filter((row) => row.message && !isGenericReasoningMessage(row.message))
}

const GENERIC_REASONING_PATTERNS = [
  'assessing schema context',
  'deciding whether more schema/data lookup is required before code generation',
]

const REASONING_SECTION_LABELS: Record<string, string> = {
  has: 'Has',
  wants: 'Wants',
  next: 'Next',
}

function isGenericReasoningMessage(message: any) {
  const normalized = String(message || '').trim().toLowerCase()
  if (!normalized) return true
  return GENERIC_REASONING_PATTERNS.some((pattern) => normalized.includes(pattern))
}

function parseReasoningSections(message: any) {
  const raw = String(message || '').trim()
  if (!raw) return []

  const normalized = raw.replace(/\r\n/g, '\n')
  const explicitSections = [
    extractReasoningSection(normalized, 'has'),
    extractReasoningSection(normalized, 'wants'),
    extractReasoningSection(normalized, 'next'),
  ].filter((section): section is { label: string; text: string } => Boolean(section?.text))

  if (explicitSections.length === 3) {
    return explicitSections
  }

  const sentenceSections = inferReasoningSectionsFromSentences(normalized)
  if (sentenceSections.length === 3) {
    return sentenceSections
  }

  return []
}

function extractReasoningSection(text: any, kind: any) {
  const patterns: Record<string, RegExp[]> = {
    has: [
      /(?:what i (?:already )?(?:have|know)|what it already has|what the assistant already has|already have|already know|has|context)\s*:\s*/i,
    ],
    wants: [
      /(?:what (?:the )?user wants|what the request needs|user wants|request|goal|wants)\s*:\s*/i,
    ],
    next: [
      /(?:what i need to do next|what happens next|next step|next|need to do next)\s*:\s*/i,
    ],
  }
  const markerPatterns = patterns[kind] || []
  for (const pattern of markerPatterns) {
    const match = pattern.exec(text)
    if (!match) continue
    const start = match.index + match[0].length
    const tail = text.slice(start)
    const nextMarker = /(?:^|\n)\s*(?:what i (?:already )?(?:have|know)|what it already has|what the assistant already has|already have|already know|has|context|what (?:the )?user wants|what the request needs|user wants|request|goal|wants|what i need to do next|what happens next|next step|next|need to do next)\s*:/im
    const nextMatch = nextMarker.exec(tail)
    const value = normalizeEphemeralText(nextMatch ? tail.slice(0, nextMatch.index) : tail)
    if (!value) continue
    return {
      label: REASONING_SECTION_LABELS[kind],
      text: value,
    }
  }
  return null
}

function inferReasoningSectionsFromSentences(text: any) {
  const sentences = String(text || '')
    .split(/(?<=[.!?])\s+/)
    .map((part) => normalizeEphemeralText(part))
    .filter(Boolean)
  if (sentences.length < 3) return []
  return [
    { label: REASONING_SECTION_LABELS.has, text: sentences[0] },
    { label: REASONING_SECTION_LABELS.wants, text: sentences[1] },
    { label: REASONING_SECTION_LABELS.next, text: sentences[2] },
  ]
}

function normalizeNodeName(nodeName: any) {
  return String(nodeName || '')
    .trim()
    .toLowerCase()
}

function describeNode(nodeName: any) {
  const normalized = normalizeNodeName(nodeName)
  if (normalized === 'agent_status') return null // handled by message field
  if (EPHEMERAL_LABELS[normalized]) return EPHEMERAL_LABELS[normalized]
  if (!normalized) return 'Processing update'
  return normalized
    .split('_')
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ')
}

function eventOutputText(event: any, message: any) {
  const type = String(event?.type || '').toLowerCase()
  const node = normalizeNodeName(event?.node)
  const stage = String(event?.stage || '').trim().toLowerCase()
  const eventMessage = String(event?.message || '').trim()
  const explicitOutput = String(event?.output || '').trim()

  if (type === 'status' && stage === 'start') {
    return ''
  }

  if (type === 'node' && node === 'create_plan') {
    const plan = streamPlanText(message)
    return plan || ''
  }

  if (type === 'status' && node === 'agent_status') {
    return explicitOutput || ''
  }

  if (eventMessage && eventMessage !== `${node} completed`) {
    return eventMessage
  }
  if (type === 'status') {
    return explicitOutput
  }
  return ''
}

function isLikelyCodeText(text: any) {
  const normalized = String(text || '').trim().toLowerCase()
  if (!normalized) return false
  const markers = [
    'import ',
    'select ',
    ' from ',
    ' group by ',
    ' order by ',
    ' limit ',
    ' conn.sql(',
    ' dataframe',
    'def ',
    'return ',
    '```',
  ]
  return markers.some((marker) => normalized.includes(marker))
}

function normalizeEphemeralText(value: any) {
  const text = String(value || '')
    .replace(/\r?\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  if (!text) return ''
  if (isLikelyCodeText(text)) return ''
  if (
    (text.startsWith('{') && text.endsWith('}')) ||
    (text.startsWith('[') && text.endsWith(']'))
  ) {
    return ''
  }
  return text
}

function ephemeralRows(message: any) {
  if (hasFinalResponse(message) && !isMessageRunning(message)) return []
  const events = streamTraceEvents(message)
  return events
    .filter((event) => {
      const type = String(event?.type || '').toLowerCase()
      const stage = String(event?.stage || '').trim().toLowerCase()
      const node = normalizeNodeName(event?.node)
      return !(type === 'status' && stage === 'start')
        && !HIDDEN_EPHEMERAL_NODES.has(node)
    })
    .map((event, index) => {
    const type = String(event?.type || '').toLowerCase()
    const node = normalizeNodeName(event?.node)
    const stage = String(event?.stage || '').trim().toLowerCase()
    const eventMessage = String(event?.message || '').trim()

    let action = 'Progress'
    if (type === 'node') {
      action = describeNode(node) || 'Processing step'
    } else if (type === 'status' && node === 'agent_status') {
      action = eventMessage || 'Progress'
    } else if (type === 'status') {
      action = String(stage || 'status')
        .split('_')
        .filter(Boolean)
        .map((part) => part[0].toUpperCase() + part.slice(1))
        .join(' ') || 'Status'
    }

    const detail = normalizeEphemeralText(eventOutputText(event, message))
    return {
      id: `${message?.id || 'msg'}-${type || 'event'}-${node || stage || index}-${index}`,
      action: normalizeEphemeralText(action) || 'Progress',
      detail,
    }
    })
    .filter((row) => row.action || row.detail)
}

function hasStreamTrace(message: any) {
  return reasoningRows(message).length > 0 || ephemeralRows(message).length > 0
}

function hasActionProgress(message: any) {
  return Boolean(
    (SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length > 0) ||
    toolActivityRows(message).length > 0
  )
}

function hasAnalysisDetails(message: any) {
  return Boolean(
    isMessageRunning(message) ||
    reasoningRows(message).length > 0 ||
    hasActionProgress(message) ||
    shouldRenderCodeDetails(message)
  )
}

function currentProgress(message: any) {
  const progressRows = ephemeralRows(message)
  const latestProgress = progressRows.at(-1)
  if (latestProgress?.action || latestProgress?.detail) {
    return {
      action: latestProgress.action || 'Analyzing your question',
      detail: latestProgress.detail || '',
    }
  }
  const latestReasoning = reasoningRows(message).at(-1)
  const nextSection = Array.isArray(latestReasoning?.sections)
    ? latestReasoning.sections.find((section: any) => section?.label === 'Next')
    : null
  if (nextSection?.text) {
    return { action: 'Planning the next step', detail: nextSection.text }
  }
  const latestTool = toolActivityRows(message).at(-1)
  if (latestTool?.tool) {
    const tool = String(latestTool.tool).replace(/_/g, ' ')
    return { action: `Using ${tool}`, detail: String(latestTool.explanation || '').trim() }
  }
  return { action: 'Analyzing your question', detail: 'Preparing the data and deciding the next step.' }
}

function hasAssistantContent(message: any) {
  return Boolean(
    message?.explanation ||
    hasAnalysisDetails(message) ||
    (SHOW_EPHEMERAL_TRACE && hasStreamTrace(message))
  )
}

function explanationHasCodeBlocks(message: any) {
  const explanation = String(message?.explanation || '')
  return /```[a-zA-Z0-9_-]*\n[\s\S]*?```/.test(explanation)
}

function shouldRenderCodeSnapshot(message: any) {
  const hasSnapshot = Boolean(String(message?.codeSnapshot || '').trim())
  if (!hasSnapshot) return false
  return !explanationHasCodeBlocks(message)
}

function shouldRenderCodeDetails(message: any) {
  return Boolean(
    String(message?.codeExplanation || '').trim() ||
    shouldRenderCodeSnapshot(message) ||
    tableUsageSummary(message)
  )
}

function openCodePane() {
  uiStore.setActiveTab('workspace')
  uiStore.setWorkspacePane('code')
}

function resolveScrollHost() {
  const localContainer = chatContainer.value
  if (!localContainer) return null
  const host = localContainer.parentElement?.closest?.('[data-chat-scroll-container]')
  return host || localContainer
}

function getScrollContainer() {
  return scrollHost.value || chatContainer.value
}

function updateScrollState(options: any = {}) {
  const fromUserScroll = options?.fromUserScroll === true
  const previousTop = Number.isFinite(options?.previousTop) ? options.previousTop : lastScrollTop
  const container = getScrollContainer()
  if (!container) {
    shouldAutoScroll = true
    showScrollToBottomButton.value = false
    lastScrollTop = 0
    return
  }
  const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
  const isNearBottomNow = distanceFromBottom <= SCROLL_THRESHOLD_PX
  if (fromUserScroll) {
    if (container.scrollTop < previousTop && distanceFromBottom > 0) {
      // Any manual upward scroll should pause auto-follow immediately.
      shouldAutoScroll = false
    } else if (isNearBottomNow) {
      shouldAutoScroll = true
    }
  } else {
    shouldAutoScroll = isNearBottomNow
  }
  showScrollToBottomButton.value = distanceFromBottom > SHOW_SCROLL_BUTTON_THRESHOLD_PX
  lastScrollTop = container.scrollTop
}

function scrollToBottom(options: any = {}) {
  const resolvedBehavior = String(options?.behavior || '').trim() || (executionStore.isConversationRunning(conversationStore.activeConversationId) ? 'auto' : 'smooth')
  const force = options?.force === true
  const hardAlign = options?.hardAlign === true
  nextTick(() => {
    const container = getScrollContainer()
    const endEl = end.value
    if (!container) return
    const behavior = resolvedBehavior
    if (force) {
      shouldAutoScroll = true
      showScrollToBottomButton.value = false
    }
    if (typeof container.scrollTo === 'function') {
      container.scrollTo({ top: container.scrollHeight, behavior })
      if (hardAlign && force && behavior === 'auto') {
        // Hydrated history needs one hard align pass after layout settles.
        window.requestAnimationFrame(() => {
          container.scrollTo({ top: container.scrollHeight, behavior: 'auto' })
          updateScrollState()
        })
        return
      }
      window.requestAnimationFrame(() => {
        updateScrollState()
      })
      return
    }
    if (!endEl) return
    endEl.scrollIntoView({ behavior, block: 'end' })
    window.requestAnimationFrame(() => {
      updateScrollState()
    })
  })
}

function handleScroll() {
  updateScrollState({ fromUserScroll: true, previousTop: lastScrollTop })
}

function handleScrollToBottomClick() {
  scrollToBottom({ behavior: 'auto', force: true })
}

async function copyCodeFromBlock(copyButton: any) {
  const block = copyButton?.closest?.('.chat-code-block')
  const codeNode = block?.querySelector('.chat-code-scroll code')
  const codeText = String(codeNode?.textContent || '').trimEnd()
  if (!codeText) return
  try {
    await navigator.clipboard.writeText(codeText)
    copyButton.setAttribute('data-copied', 'true')
    window.setTimeout(() => copyButton.removeAttribute('data-copied'), 1200)
    toast.success('Copied!', 'Code block copied to clipboard')
  } catch (error: any) {
    console.error('Failed to copy code block:', error)
    toast.error('Copy failed', 'Unable to copy code block')
  }
}

function handleChatContainerClick(event: any) {
  const target = event?.target instanceof Element ? event.target : null
  if (!target) return
  const copyButton = target.closest('.chat-code-copy')
  if (!copyButton) return
  event.preventDefault()
  void copyCodeFromBlock(copyButton)
}

// Watch for chat history changes and auto-scroll if user is near bottom
watch([() => displayedChatHistory.value.length, lastMessageId], ([newLength], [oldLength]) => {
  const previousLength = Number.isFinite(oldLength) ? oldLength : 0
  if (shouldAutoScroll && newLength > previousLength) {
    nextTick(() => scrollToBottom())
  }
})

watch(() => conversationStore.activeConversationId, () => {
  shouldAutoScroll = true
  nextTick(() => scrollToBottom())
})

// Watch for loading state changes
watch(() => executionStore.isConversationRunning(conversationStore.activeConversationId), (isLoading, wasLoading) => {
  if (wasLoading && !isLoading) {
  }
  if (shouldAutoScroll) {
    nextTick(() => scrollToBottom())
  }
})
</script>

<style scoped>
:deep(.chat-ref-highlight) {
  color: var(--color-info-text);
  font-style: italic;
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 2px;
}

:deep(.chat-markdown-content) {
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text-main);
  font-weight: 400;
}

:deep(.final-response-body) {
  font-size: 14px;
  line-height: 1.6;
  font-weight: 400;
}

.user-turn-bubble {
  position: relative;
  border: 1px solid color-mix(in srgb, var(--color-accent) 14%, var(--color-border));
  background-color: var(--color-chat-user-bubble);
  box-shadow: 0 2px 10px -4px color-mix(in srgb, var(--color-text-main) 6%, transparent);
  border-radius: 0.875rem !important;
}


.stream-reasoning-list {
  display: grid;
  gap: 0.7rem;
}

.stream-reasoning-item {
  border-left: 2px solid var(--color-accent);
  padding-left: 0.75rem;
}

.stream-reasoning-section + .stream-reasoning-section {
  margin-top: 0.55rem;
}

.stream-reasoning-label {
  margin: 0;
  font-size: 0.68rem;
  line-height: 1.25;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-accent);
}

.stream-reasoning-text {
  margin: 0.18rem 0 0;
  font-size: 0.875rem;
  line-height: 1.58;
  color: color-mix(in srgb, var(--color-text-main) 90%, var(--color-text-muted) 10%);
}

.stream-action-section {
  position: relative;
  display: grid;
  gap: 1rem;
  margin-top: 1.05rem;
  padding-top: 0.7rem;
}

.ephemeral-trace-list {
  display: grid;
  gap: 1.15rem;
}

.ephemeral-trace-item {
  margin: 0;
}

.ephemeral-trace-action {
  margin: 0;
  font-size: 0.96rem;
  line-height: 1.7;
  color: var(--color-text-main);
}

.ephemeral-trace-detail {
  margin: 0.1rem 0 0;
  font-size: 0.875rem;
  line-height: 1.58;
  color: color-mix(in srgb, var(--color-text-main) 90%, var(--color-text-muted) 10%);
}

.view-code-details {
  margin-top: 0.6rem;
}

.view-code-toggle {
  display: inline-flex;
  list-style: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-text-muted);
  text-decoration: none;
}

.view-code-toggle::-webkit-details-marker {
  display: none;
}

.view-code-toggle:hover {
  color: var(--color-text-main);
}

.view-code-caret {
  transition: transform 130ms ease;
}

.view-code-details-open .view-code-caret {
  transform: rotate(180deg);
}

.view-code-panel {
  margin-top: 0.4rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  background-color: color-mix(in srgb, var(--color-surface) 88%, var(--color-workspace-surface));
  padding: 0.7rem 0.9rem 0.9rem;
}

.live-progress-status {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding-bottom: 0.75rem;
  color: var(--color-text-main);
}

.live-progress-status + .stream-reasoning-list,
.live-progress-status + .stream-action-section {
  padding-top: 0.75rem;
  border-top: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
}

.live-progress-action {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
  color: var(--color-text-main);
}

.live-progress-detail {
  margin: 0.1875rem 0 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.live-progress-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 9999px;
  background: var(--color-accent);
  box-shadow: 0 0 0 0.1875rem color-mix(in srgb, var(--color-accent) 12%, transparent);
  animation: live-progress-pulse 1.5s var(--motion-ease-standard) infinite;
}

.view-code-meta-badge {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 9999px;
  padding: 0.15rem 0.55rem;
  font-size: 0.69rem;
  color: var(--color-text-muted);
  background-color: color-mix(in srgb, var(--color-surface) 92%, transparent);
}

:deep(.chat-markdown-content strong),
:deep(.chat-markdown-content em),
:deep(.chat-markdown-content a) {
  color: var(--color-text-main);
}

:deep(.chat-markdown-content a) {
  text-decoration: underline;
}

:deep(.chat-markdown-content p) {
  margin: 0.65rem 0;
  color: var(--color-text-main);
}

:deep(.chat-markdown-content h1),
:deep(.chat-markdown-content h2),
:deep(.chat-markdown-content h3),
:deep(.chat-markdown-content h4) {
  margin-top: 1.15rem;
  margin-bottom: 0.65rem;
  line-height: 1.3;
}

:deep(.chat-markdown-content h1:first-child),
:deep(.chat-markdown-content h2:first-child),
:deep(.chat-markdown-content h3:first-child),
:deep(.chat-markdown-content h4:first-child),
:deep(.chat-markdown-content p:first-child) {
  margin-top: 0;
}

:deep(.chat-markdown-content ol),
:deep(.chat-markdown-content ul) {
  margin: 0.7rem 0 0.95rem;
  padding-left: 1.25rem;
}

:deep(.chat-markdown-content li) {
  margin: 0.35rem 0;
  color: var(--color-text-main);
}

.analyzing-status {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  color: var(--color-text-main);
}

.analyzing-spinner {
  width: 0.85rem;
  height: 0.85rem;
  border: 1.5px solid color-mix(in srgb, var(--color-text-muted) 22%, transparent);
  border-top-color: var(--color-accent-text);
  border-radius: 9999px;
  animation: analyzing-spin 0.9s linear infinite;
}

.analyzing-status-text {
  position: relative;
  display: inline-block;
  overflow: hidden;
  color: var(--color-text-main);
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.35;
}

.analyzing-status-text::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-120%);
  background: linear-gradient(
    110deg,
    transparent 0%,
    transparent 35%,
    color-mix(in srgb, var(--color-surface) 85%, transparent) 50%,
    transparent 65%,
    transparent 100%
  );
  animation: analyzing-glimmer 1.65s ease-in-out infinite;
}

@keyframes analyzing-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes analyzing-glimmer {
  to {
    transform: translateX(120%);
  }
}

@keyframes live-progress-pulse {
  50% {
    opacity: 0.55;
    transform: scale(0.82);
  }
}

@media (prefers-reduced-motion: reduce) {
  .analyzing-spinner,
  .analyzing-status-text::after,
  .live-progress-dot {
    animation: none;
  }
}

:deep(.chat-markdown-content .chat-code-block) {
  margin: 1rem 0 1.2rem;
}

:deep(.chat-code-block),
.chat-code-block {
  border: 1px solid var(--color-border);
  border-radius: 14px;
  overflow: hidden;
  background-color: var(--color-base);
}

:deep(.chat-code-header),
.chat-code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-border);
  background-color: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: lowercase;
}

:deep(.chat-code-copy),
.chat-code-copy {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--color-text-muted);
  background-color: transparent;
  transition: background-color 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}

:deep(.chat-code-copy:hover),
.chat-code-copy:hover {
  border-color: var(--color-border);
  background-color: color-mix(in srgb, var(--color-surface) 80%, transparent);
  color: var(--color-text-main);
}

:deep(.chat-code-copy:focus-visible),
.chat-code-copy:focus-visible {
  outline: none;
  border-color: var(--color-border-hover);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-border-hover) 32%, transparent);
}

:deep(.chat-code-copy[data-copied="true"]),
.chat-code-copy[data-copied="true"] {
  border-color: var(--color-success) !important;
  background-color: var(--color-success-bg) !important;
  color: var(--color-success) !important;
}

:deep(.chat-code-copy[data-copied="true"] svg),
.chat-code-copy[data-copied="true"] svg {
  display: none;
}

:deep(.chat-code-copy[data-copied="true"]::after),
.chat-code-copy[data-copied="true"]::after {
  content: '✓';
  font-size: 14px;
  font-weight: bold;
  color: var(--color-success);
}

:deep(.chat-code-copy svg),
.chat-code-copy svg {
  width: 17px;
  height: 17px;
}

:deep(.chat-code-scroll),
.chat-code-scroll {
  margin: 0;
  padding: 18px 16px;
  max-height: 320px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.6;
  font-weight: 400;
  background-color: var(--color-base);
  color: var(--color-text-main);
}

:deep(.chat-code-scroll code),
.chat-code-scroll code {
  font-family: var(--font-mono);
  white-space: pre;
}

:deep(.chat-code-scroll .token.comment),
.chat-code-scroll .token.comment {
  color: var(--color-text-muted);
}

:deep(.chat-code-scroll .token.keyword),
.chat-code-scroll .token.keyword {
  color: var(--color-accent);
}

:deep(.chat-code-scroll .token.string),
.chat-code-scroll .token.string {
  color: var(--color-success);
}

:deep(.chat-code-scroll .token.number),
.chat-code-scroll .token.number {
  color: var(--color-info-text);
}

:deep(.chat-code-scroll .token.function),
.chat-code-scroll .token.function {
  color: var(--color-info);
}

:deep(.chat-code-scroll .token.operator),
.chat-code-scroll .token.operator {
  color: var(--color-text-main);
}
</style>
