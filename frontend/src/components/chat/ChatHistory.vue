<template>
  <div ref="chatContainer" class="space-y-4" style="min-height: 200px;" role="log" aria-live="polite" aria-relevant="additions" :aria-busy="appStore.isLoading">
    <div v-if="appStore.activeConversationId && appStore.turnsNextCursor" class="flex justify-center">
      <button
        type="button"
        class="text-xs px-3 py-1.5 rounded-full border transition-colors"
        style="border-color: var(--color-border); background-color: var(--color-surface); color: var(--color-text-muted);"
        @click="loadMoreTurns"
      >
        Load more
      </button>
    </div>

    <!-- Loading indicator for first message when no history yet -->
    <div v-if="appStore.isLoading && appStore.chatHistory.length === 0" role="status" aria-live="polite" class="flex items-center justify-center py-6">
      <div class="analyzing-status">
        <div class="analyzing-spinner" aria-hidden="true"></div>
        <span class="analyzing-status-text">Analyzing your question...</span>
      </div>
    </div>

    <div
      v-for="message in appStore.chatHistory"
      :key="message.id"
      class="group"
    >
      <!-- User Message -->
      <div class="w-full mb-1">
        <div class="user-turn-bubble px-3 py-2.5 rounded-2xl rounded-tl-sm">
          <button
            @click.stop="copyQuestion(message.question)"
            type="button"
            aria-label="Copy question"
            class="user-turn-copy-btn"
            title="Copy question"
          >
            <DocumentDuplicateIcon class="h-3.5 w-3.5" />
          </button>
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
        <div class="mt-1 px-1">
          <p class="text-[12px] font-normal leading-[1.3]" style="color: var(--color-text-muted);">{{ formatTimestamp(message.timestamp) }}</p>
        </div>
      </div>

      <!-- Assistant Response -->
      <div v-if="hasAssistantContent(message)" class="w-full group">
        <div class="px-3 py-2.5 rounded-2xl rounded-tl-sm" style="background-color: transparent">
          <div v-if="reasoningRows(message).length" class="stream-reasoning-list">
            <div v-for="row in reasoningRows(message)" :key="row.id" class="stream-reasoning-item">
              <p class="stream-reasoning-label">Understanding</p>
              <p class="stream-reasoning-text">{{ row.message }}</p>
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

          <AgentIntervention
            v-if="pendingIntervention(message)"
            class="mt-3"
            :intervention="pendingIntervention(message)"
            :busy="isMessageInterventionBusy(message)"
            @respond="(payload) => submitInterventionResponse(message, payload)"
          />

          <div
            v-if="message.explanation"
            class="mt-4 mb-3 flex items-center gap-3"
          >
            <div class="h-px flex-1" style="background-color: var(--color-border);"></div>
            <span class="text-[11px] uppercase tracking-[0.08em] font-medium" style="color: var(--color-accent);">Final response</span>
            <div class="h-px flex-1" style="background-color: var(--color-border);"></div>
          </div>

          <div v-if="message.explanation" class="chat-markdown-content final-response-body max-w-none" style="color: var(--color-text-main);">
            <div v-html="renderMarkdown(message.explanation)"></div>
          </div>

          <details v-if="shouldRenderCodeDetails(message)" class="mt-2 view-code-details">
            <summary class="view-code-toggle">
              <span class="inline-flex items-center gap-1.5">
                <CodeBracketIcon class="h-4 w-4" title="View code details" />
                <span>View code</span>
                <span class="view-code-caret" aria-hidden="true">↓</span>
              </span>
            </summary>
            <div class="view-code-panel">
              <div v-if="tableUsageSummary(message)" class="mb-3">
                <span class="view-code-meta-badge">{{ tableUsageSummary(message) }}</span>
              </div>
              <div
                v-if="message.codeExplanation"
                class="chat-markdown-content text-[14px] leading-[1.7] max-w-none mb-3"
                style="color: var(--color-text-main);"
              >
                <div v-html="renderMarkdown(message.codeExplanation)"></div>
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
                <pre class="chat-code-scroll"><code class="language-python" v-html="renderCodeSnapshot(message.codeSnapshot)"></code></pre>
              </div>
            </div>
          </details>

        </div>
        <div v-if="message.explanation" class="flex items-center justify-end mt-1 px-4">
          <div class="flex items-center space-x-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
            <button
              @click="copyExplanation(message.explanation)"
              type="button"
              aria-label="Copy explanation"
              class="btn-icon text-xs p-1"
              title="Copy explanation"
            >
              <DocumentDuplicateIcon class="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading indicator when analyzing - shown below last message -->
    <div v-if="appStore.isLoading && appStore.chatHistory.length > 0" role="status" aria-live="polite" class="flex items-center justify-center py-6">
      <div class="analyzing-status">
        <div class="analyzing-spinner" aria-hidden="true"></div>
        <span class="analyzing-status-text">Analyzing your question...</span>
      </div>
    </div>

    <!-- Placeholder message when no chat history -->
    <div v-once v-if="appStore.chatHistory.length === 0 && !appStore.isLoading" class="flex items-center justify-center py-12">
      <div class="text-center">
        <div class="mb-4" style="color: var(--color-border-hover);">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 class="text-lg font-medium mb-2" style="color: var(--color-text-main);">Start Your Analysis</h3>
        <p style="color: var(--color-text-muted);">Ask a question about your data to begin the conversation.</p>
      </div>
    </div>

    <div v-if="showScrollToBottomButton" class="sticky bottom-3 z-20 flex justify-end pr-2 pointer-events-none">
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

    <!-- Sentinel for auto-scroll -->
    <div ref="end" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import {
  DocumentDuplicateIcon,
  ChevronDownIcon,
  CodeBracketIcon,
} from '@heroicons/vue/24/outline'
import ToolActivityCard from './ToolActivityCard.vue'
import AgentIntervention from './AgentIntervention.vue'
import { toolOutputHasRenderableContent } from '../../utils/toolOutputPreview'
import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'
import DOMPurify from 'dompurify'
import Prism from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-sql'
import { formatTimestamp } from '../../utils/dateUtils'
import { toast } from '../../composables/useToast'
import 'katex/dist/katex.min.css'

// Configure DOMPurify to add security attributes to links
DOMPurify.addHook('afterSanitizeAttributes', function(node) {
  if (node.tagName === 'A' && node.getAttribute('href')) {
    node.setAttribute('rel', 'noopener noreferrer')
    node.setAttribute('target', '_blank')
  }
})


const appStore = useAppStore()
const chatContainer = ref(null)
const scrollHost = ref(null)
const end = ref(null)
const pendingInterventionIds = ref(new Set())
const SHOW_EPHEMERAL_TRACE = true
const showScrollToBottomButton = ref(false)
let shouldAutoScroll = true
let mutationObserver = null
let lastScrollTop = 0

const lastMessageId = computed(() => appStore.chatHistory.at(-1)?.id)

const SCROLL_THRESHOLD_PX = 100
const SHOW_SCROLL_BUTTON_THRESHOLD_PX = 220
const QUESTION_REFERENCE_RE = /\b[A-Za-z_][A-Za-z0-9_]*\."(?:[^"]|"")+"|\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*/g

function attachmentPreviewSrc(attachment) {
  const mediaType = String(attachment?.media_type || 'image/png').trim()
  const dataBase64 = String(attachment?.data_base64 || '').trim()
  if (!dataBase64) return ''
  return `data:${mediaType};base64,${dataBase64}`
}

function tableUsageSummary(message) {
  const metadata = message?.analysisMetadata
  if (!metadata || typeof metadata !== 'object') return ''
  const tables = Array.isArray(metadata.tables_used)
    ? metadata.tables_used.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (tables.length === 0) return ''
  const joinsUsed = Boolean(metadata.joins_used)
  const joinKeys = Array.isArray(metadata.join_keys)
    ? metadata.join_keys.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (!joinsUsed) {
    return `Tables used: ${tables.join(', ')}`
  }
  if (joinKeys.length > 0) {
    return `Tables used: ${tables.join(', ')} · Join keys: ${joinKeys.join(', ')}`
  }
  return `Tables used: ${tables.join(', ')} · Conservative join`
}

function escapeHtml(rawValue) {
  return String(rawValue || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderQuestionWithHighlights(question) {
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

// Markdown parser
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true
})
md.use(markdownItKatex)

function resolvePrismLanguage(rawLanguage) {
  const normalized = String(rawLanguage || '').trim().toLowerCase()
  if (!normalized) return 'python'
  if (normalized === 'python' || normalized === 'py') return 'python'
  if (
    normalized === 'sql' ||
    normalized === 'sqlite' ||
    normalized === 'duckdb' ||
    normalized === 'postgres' ||
    normalized === 'postgresql'
  ) return 'sql'
  return 'python'
}

md.renderer.rules.fence = (tokens, idx) => {
  const token = tokens[idx]
  const rawInfo = String(token.info || '').trim()
  const requestedLanguage = rawInfo.split(/\s+/).filter(Boolean)[0] || 'python'
  const prismLanguage = resolvePrismLanguage(requestedLanguage)
  const langEscaped = md.utils.escapeHtml(prismLanguage)
  const rawCode = String(token.content || '')
  const grammar = Prism.languages[prismLanguage]
  const highlightedCode = grammar
    ? Prism.highlight(rawCode, grammar, prismLanguage)
    : md.utils.escapeHtml(rawCode)
  const copyIconSvg = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<rect x="9" y="9" width="13" height="13" rx="2"></rect>' +
      '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>' +
    '</svg>'
  )

  return (
    `<div class="chat-code-block">` +
      `<div class="chat-code-header">` +
        `<span>${langEscaped}</span>` +
        `<button type="button" class="chat-code-copy" aria-label="Copy code" title="Copy code">${copyIconSvg}</button>` +
      `</div>` +
      `<pre class="chat-code-scroll"><code class="language-${langEscaped}">${highlightedCode}</code></pre>` +
    `</div>`
  )
}

const EPHEMERAL_LABELS = {
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
  if (appStore.chatHistory.length > 0) {
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


async function copyQuestion(question) {
  try {
    await navigator.clipboard.writeText(question)
    toast.success('Copied!', 'Question copied to clipboard')
  } catch (error) {
    console.error('Failed to copy question:', error)
    toast.error('Copy failed', 'Unable to copy question to clipboard')
  }
}

async function copyExplanation(explanation) {
  try {
    await navigator.clipboard.writeText(explanation)
    toast.success('Copied!', 'Explanation copied to clipboard')
  } catch (error) {
    console.error('Failed to copy explanation:', error)
    toast.error('Copy failed', 'Unable to copy explanation to clipboard')
  }
}

function renderMarkdown(text) {
  if (!text) return ''
  const normalized = String(text)
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
  const html = md.render(normalized)
  return DOMPurify.sanitize(html, {
    ADD_TAGS: ['button', 'svg', 'rect', 'path'],
    ADD_ATTR: [
      'aria-hidden',
      'aria-label',
      'class',
      'fill',
      'stroke',
      'stroke-width',
      'stroke-linecap',
      'stroke-linejoin',
      'title',
      'type',
      'viewBox',
      'x',
      'y',
      'width',
      'height',
      'rx',
      'd'
    ]
  })
}

function renderCodeSnapshot(code) {
  const rawCode = String(code || '')
  if (!rawCode) return ''
  const grammar = Prism.languages.python
  const highlighted = grammar
    ? Prism.highlight(rawCode, grammar, 'python')
    : md.utils.escapeHtml(rawCode)
  return DOMPurify.sanitize(highlighted, {
    ALLOWED_TAGS: ['span'],
    ALLOWED_ATTR: ['class']
  })
}

function streamPlanText(message) {
  return String(message?.streamTrace?.planText || '').trim()
}

function streamTraceEvents(message) {
  const events = message?.streamTrace?.events
  return Array.isArray(events) ? events : []
}

function streamReasoningEvents(message) {
  const events = message?.streamTrace?.reasoning
  return Array.isArray(events) ? events : []
}

function streamToolCalls(message) {
  const calls = message?.streamTrace?.toolCalls
  return Array.isArray(calls) ? calls : []
}

function toolActivityRows(message) {
  return streamToolCalls(message).filter((activity) => String(activity?.tool || '').trim().toLowerCase() !== 'execute_python')
}

function isToolActivityOutputCollapsed(message, activityIndex) {
  const rows = toolActivityRows(message)
  const activity = rows[activityIndex]
  if (!toolOutputHasRenderableContent(activity)) return false
  if (String(message?.explanation || '').trim()) return true
  return rows
    .slice(activityIndex + 1)
    .some((nextActivity) => toolOutputHasRenderableContent(nextActivity))
}

function pendingIntervention(message) {
  const intervention = message?.streamTrace?.intervention
  if (!intervention || typeof intervention !== 'object') return null
  return intervention
}

function reasoningRows(message) {
  return streamReasoningEvents(message)
    .map((event, index) => ({
      id: `${message?.id || 'msg'}-reasoning-${String(event?.stage || 'intent')}-${index}`,
      message: normalizeEphemeralText(event?.message),
    }))
    .filter((row) => row.message)
}

function normalizeNodeName(nodeName) {
  return String(nodeName || '')
    .trim()
    .toLowerCase()
}

function describeNode(nodeName) {
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

function eventOutputText(event, message) {
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

function isLikelyCodeText(text) {
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

function normalizeEphemeralText(value) {
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

function ephemeralRows(message) {
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

function hasStreamTrace(message) {
  return reasoningRows(message).length > 0 || ephemeralRows(message).length > 0
}

function hasActionProgress(message) {
  return Boolean(
    (SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length > 0) ||
    toolActivityRows(message).length > 0
  )
}

function hasAssistantContent(message) {
  return Boolean(
    message?.explanation ||
    shouldRenderCodeDetails(message) ||
    toolActivityRows(message).length > 0 ||
    pendingIntervention(message) ||
    (SHOW_EPHEMERAL_TRACE && hasStreamTrace(message))
  )
}

function explanationHasCodeBlocks(message) {
  const explanation = String(message?.explanation || '')
  return /```[a-zA-Z0-9_-]*\n[\s\S]*?```/.test(explanation)
}

function shouldRenderCodeSnapshot(message) {
  const hasSnapshot = Boolean(String(message?.codeSnapshot || '').trim())
  if (!hasSnapshot) return false
  return !explanationHasCodeBlocks(message)
}

function shouldRenderCodeDetails(message) {
  return Boolean(
    String(message?.codeExplanation || '').trim() ||
    shouldRenderCodeSnapshot(message) ||
    tableUsageSummary(message)
  )
}

function openCodePane() {
  appStore.setActiveTab('workspace')
  appStore.setWorkspacePane('code')
}

async function loadMoreTurns() {
  try {
    await appStore.fetchConversationTurns({ reset: false })
  } catch (error) {
    console.error('Failed to load more turns:', error)
  }
}

function isInterventionBusy(interventionId) {
  return pendingInterventionIds.value.has(String(interventionId || ''))
}

function isMessageInterventionBusy(message) {
  const interventionId = String(message?.streamTrace?.intervention?.id || '')
  if (!interventionId) return false
  return isInterventionBusy(interventionId)
}

async function submitInterventionResponse(message, payload) {
  const interventionId = String(payload?.id || '')
  if (!interventionId || isInterventionBusy(interventionId)) return
  pendingInterventionIds.value.add(interventionId)
  try {
    const selected = Array.isArray(payload?.selected) ? payload.selected.map((item) => String(item || '')) : []
    const response = await apiService.v1RespondChatIntervention(interventionId, selected)
    const accepted = Boolean(response?.accepted)
    if (!accepted) {
      throw new Error('Intervention response was rejected.')
    }
    if (message?.streamTrace?.intervention && String(message.streamTrace.intervention.id || '') === interventionId) {
      message.streamTrace.intervention.selected = selected
      message.streamTrace.intervention.status = 'submitted'
      message.streamTrace.intervention.responded_at = new Date().toISOString()
    }
  } catch (error) {
    console.error('Failed to submit intervention response:', error)
    if (message?.streamTrace?.intervention && String(message.streamTrace.intervention.id || '') === interventionId) {
      message.streamTrace.intervention.status = 'error'
    }
    toast.error('Intervention failed', 'Unable to send your response. Please try again.')
  } finally {
    pendingInterventionIds.value.delete(interventionId)
  }
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

function updateScrollState(options = {}) {
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

function scrollToBottom(options = {}) {
  const resolvedBehavior = String(options?.behavior || '').trim() || (appStore.isLoading ? 'auto' : 'smooth')
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

async function copyCodeFromBlock(copyButton) {
  const block = copyButton?.closest?.('.chat-code-block')
  const codeNode = block?.querySelector('.chat-code-scroll code')
  const codeText = String(codeNode?.textContent || '').trimEnd()
  if (!codeText) return
  try {
    await navigator.clipboard.writeText(codeText)
    copyButton.setAttribute('data-copied', 'true')
    window.setTimeout(() => copyButton.removeAttribute('data-copied'), 1200)
    toast.success('Copied!', 'Code block copied to clipboard')
  } catch (error) {
    console.error('Failed to copy code block:', error)
    toast.error('Copy failed', 'Unable to copy code block')
  }
}

function handleChatContainerClick(event) {
  const target = event?.target instanceof Element ? event.target : null
  if (!target) return
  const copyButton = target.closest('.chat-code-copy')
  if (!copyButton) return
  event.preventDefault()
  void copyCodeFromBlock(copyButton)
}

// Watch for chat history changes and auto-scroll if user is near bottom
watch([() => appStore.chatHistory.length, lastMessageId], ([newLength], [oldLength]) => {
  const previousLength = Number.isFinite(oldLength) ? oldLength : 0
  if (shouldAutoScroll && newLength > previousLength) {
    nextTick(() => scrollToBottom())
  }
})

watch(() => appStore.activeConversationId, () => {
  shouldAutoScroll = true
  nextTick(() => scrollToBottom())
})

// Watch for loading state changes
watch(() => appStore.isLoading, (isLoading, wasLoading) => {
  if (wasLoading && !isLoading) {
    pendingInterventionIds.value.clear()
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
  line-height: 1.7;
  color: var(--color-text-main);
  font-weight: 400;
}

:deep(.final-response-body) {
  font-size: 14px;
  line-height: 1.7;
  font-weight: 400;
}

.user-turn-bubble {
  position: relative;
  border: 1px solid color-mix(in srgb, var(--color-accent) 22%, var(--color-border));
  background-color: var(--color-chat-user-bubble);
}

.user-turn-copy-btn {
  position: absolute;
  top: 0.375rem;
  right: 0.375rem;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid transparent;
  color: var(--color-text-muted);
  background: transparent;
  opacity: 0;
  transition: opacity 120ms ease, background-color 120ms ease, border-color 120ms ease, color 120ms ease;
}

.group:hover .user-turn-copy-btn,
.group:focus-within .user-turn-copy-btn {
  opacity: 1;
}

.user-turn-copy-btn:hover {
  color: var(--color-text-main);
  border-color: var(--color-border);
  background-color: color-mix(in srgb, var(--color-surface) 78%, transparent);
}

.stream-reasoning-list {
  display: grid;
  gap: 0.7rem;
}

.stream-reasoning-item {
  border-left: 2px solid var(--color-accent);
  padding-left: 0.75rem;
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
  gap: 0.95rem;
  margin-top: 1.15rem;
  padding-top: 1.05rem;
}

.stream-action-section::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0.75rem;
  width: 1.5rem;
  height: 1px;
  background-color: color-mix(in srgb, var(--color-border) 86%, transparent);
}

.ephemeral-trace-list {
  display: grid;
  gap: 1rem;
}

.ephemeral-trace-item {
  margin: 0;
}

.ephemeral-trace-action {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.3;
  letter-spacing: 0.01em;
  color: color-mix(in srgb, var(--color-text-muted) 90%, var(--color-text-main) 10%);
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

.view-code-details[open] .view-code-caret {
  transform: rotate(180deg);
}

.view-code-panel {
  margin-top: 0.4rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  background-color: color-mix(in srgb, var(--color-surface) 88%, var(--color-workspace-surface));
  padding: 0.7rem 0.9rem 0.9rem;
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

@media (prefers-reduced-motion: reduce) {
  .analyzing-spinner,
  .analyzing-status-text::after {
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
  border-color: var(--color-border);
  background-color: color-mix(in srgb, var(--color-surface) 80%, transparent);
  color: var(--color-text-main);
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
