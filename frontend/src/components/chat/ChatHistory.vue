<template>
  <div ref="chatContainer" class="space-y-6" style="min-height: 200px;" role="log" aria-live="polite" aria-relevant="additions" :aria-busy="appStore.isLoading">
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
      <div class="flex items-center space-x-3 px-4 py-3 rounded-xl shadow-sm" style="color: var(--color-text-muted); background-color: color-mix(in srgb, var(--color-base) 60%, var(--color-border) 40%);">
        <div class="animate-spin rounded-full h-5 w-5 border-2" style="border-color: var(--color-border); border-top-color: var(--color-text-muted);" aria-hidden="true"></div>
        <span class="text-sm font-medium">Analyzing your question...</span>
      </div>
    </div>

    <div
      v-for="message in appStore.chatHistory"
      :key="message.id"
      class="group"
    >
      <!-- User Message -->
      <div class="w-full mb-2">
        <div class="px-4 py-3 rounded-2xl rounded-tl-sm" style="background-color: #EDE9DE;">
          <p
            class="chat-question-text text-sm whitespace-pre-wrap"
            style="color: var(--color-text-main);"
            v-html="renderQuestionWithHighlights(message.question)"
          ></p>
        </div>
        <div class="flex items-center justify-between mt-1 px-1">
          <p class="text-xs" style="color: var(--color-text-muted);">{{ formatTimestamp(message.timestamp) }}</p>
          <div class="flex items-center space-x-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
            <button
              @click="copyQuestion(message.question)"
              type="button"
              aria-label="Copy question"
              class="btn-icon text-xs p-1"
              title="Copy question"
            >
              <DocumentDuplicateIcon class="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>

      <!-- Assistant Response -->
      <div v-if="hasAssistantContent(message)" class="w-full group">
        <div class="px-4 py-3 rounded-2xl rounded-tl-sm" style="background-color: transparent">
          <div v-if="SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length" class="space-y-3">
            <div v-for="row in ephemeralRows(message)" :key="row.id">
              <button
                v-if="row.output"
                type="button"
                class="inline-flex items-center gap-1.5 text-sm font-medium"
                style="color: var(--color-text-muted);"
                @click="toggleEphemeralRow(row.id)"
              >
                <ChevronRightIcon
                  v-if="!isEphemeralRowExpanded(row.id)"
                  class="h-3.5 w-3.5"
                  aria-hidden="true"
                />
                <ChevronDownIcon
                  v-else
                  class="h-3.5 w-3.5"
                  aria-hidden="true"
                />
                <span>{{ row.summary }}</span>
              </button>
              <p
                v-else
                class="text-sm font-medium"
                style="color: var(--color-text-muted);"
              >
                {{ row.summary }}
              </p>
              <div
                v-if="row.output && isEphemeralRowExpanded(row.id)"
                class="mt-1 pl-5 chat-markdown-content text-sm leading-relaxed max-w-none"
                style="color: var(--color-text-main);"
              >
                <div v-html="renderMarkdown(row.output)"></div>
              </div>
            </div>
          </div>

          <div v-if="toolActivityRows(message).length" class="space-y-3 mt-3">
            <ToolActivityCard
              v-for="activity in toolActivityRows(message)"
              :key="activity.call_id || activity.started_at"
              :activity="activity"
            />
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
            <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">Final response</span>
            <div class="h-px flex-1" style="background-color: var(--color-border);"></div>
          </div>

          <div v-if="message.explanation" class="chat-markdown-content text-sm leading-relaxed max-w-none" style="color: var(--color-text-main);">
            <div v-html="renderMarkdown(message.explanation)"></div>
          </div>

          <details v-if="shouldRenderCodeDetails(message)" class="mt-3 rounded-xl border code-details-panel" style="border-color: var(--color-border);">
            <summary class="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium" style="color: var(--color-text-main);">
              <span>Generated code details</span>
              <span class="text-xs uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Optional</span>
            </summary>
            <div class="px-4 pb-4 pt-1">
              <div
                v-if="message.codeExplanation"
                class="chat-markdown-content text-sm leading-relaxed max-w-none mb-3"
                style="color: var(--color-text-main);"
              >
                <div v-html="renderMarkdown(message.codeExplanation)"></div>
              </div>
              <div v-if="shouldRenderCodeSnapshot(message)" class="chat-code-block">
                <div class="chat-code-header">
                  <span>python</span>
                  <button
                    type="button"
                    class="text-xs font-medium underline-offset-2 hover:underline"
                    style="color: #A1A1AA;"
                    @click="openCodePane"
                  >
                    Open Code
                  </button>
                </div>
                <pre class="chat-code-scroll"><code class="language-python" v-html="renderCodeSnapshot(message.codeSnapshot)"></code></pre>
              </div>
            </div>
          </details>

          <details v-if="message.toolEvents && message.toolEvents.length" class="mt-3 rounded p-2" style="border: 1px solid var(--color-border);">
            <summary class="text-xs cursor-pointer" style="color: var(--color-text-muted);">Tool artifacts</summary>
            <pre class="text-xs whitespace-pre-wrap mt-2 max-h-48 overflow-auto" style="color: var(--color-text-main);">{{ formatToolEvents(message.toolEvents) }}</pre>
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
      <div class="flex items-center space-x-3 px-4 py-3 rounded-xl shadow-sm" style="color: var(--color-text-muted); background-color: color-mix(in srgb, var(--color-base) 60%, var(--color-border) 40%);">
        <div class="animate-spin rounded-full h-5 w-5 border-2" style="border-color: var(--color-border); border-top-color: var(--color-text-muted);" aria-hidden="true"></div>
        <span class="text-sm font-medium">Analyzing your question...</span>
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
  ChevronRightIcon,
  ChevronDownIcon
} from '@heroicons/vue/24/outline'
import ToolActivityCard from './ToolActivityCard.vue'
import AgentIntervention from './AgentIntervention.vue'
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
const ephemeralExpandedRows = ref(new Set())
const pendingInterventionIds = ref(new Set())
const suppressMutationAutoScroll = ref(false)
const SHOW_EPHEMERAL_TRACE = true
const showScrollToBottomButton = ref(false)
let shouldAutoScroll = true
let mutationObserver = null
let lastScrollTop = 0

const lastMessageId = computed(() => appStore.chatHistory.at(-1)?.id)

const SCROLL_THRESHOLD_PX = 100
const SHOW_SCROLL_BUTTON_THRESHOLD_PX = 220
const QUESTION_REFERENCE_RE = /\b[A-Za-z_][A-Za-z0-9_]*\."(?:[^"]|"")+"|\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*/g

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
      if (suppressMutationAutoScroll.value) return
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

function formatToolEvents(events) {
  try {
    return JSON.stringify(events, null, 2)
  } catch (_error) {
    return String(events)
  }
}

function streamPlanText(message) {
  return String(message?.streamTrace?.planText || '').trim()
}

function streamTraceEvents(message) {
  const events = message?.streamTrace?.events
  return Array.isArray(events) ? events : []
}

function streamToolCalls(message) {
  const calls = message?.streamTrace?.toolCalls
  return Array.isArray(calls) ? calls : []
}

function toolActivityRows(message) {
  return streamToolCalls(message).filter((activity) => String(activity?.tool || '').trim().toLowerCase() !== 'execute_python')
}

function pendingIntervention(message) {
  const intervention = message?.streamTrace?.intervention
  if (!intervention || typeof intervention !== 'object') return null
  return intervention
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

  if (explicitOutput) return explicitOutput

  if (type === 'status' && stage === 'start') {
    return ''
  }

  if (type === 'node' && node === 'create_plan') {
    const plan = streamPlanText(message)
    return plan || ''
  }

  if (eventMessage && eventMessage !== `${node} completed`) {
    return eventMessage
  }
  return ''
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

    let summary = 'Processing update'
    if (node === 'agent_status') {
      summary = String(event?.message || 'Processing...')
    } else if (type === 'status') {
      summary = String(event?.message || 'Updating analysis status')
    } else if (type === 'node') {
      summary = describeNode(node) || String(event?.message || 'Processing update')
    }

    const output = eventOutputText(event, message)
    return {
      id: `${message?.id || 'msg'}-${type || 'event'}-${node || stage || index}-${index}`,
      summary,
      output
    }
    })
}

function hasStreamTrace(message) {
  return ephemeralRows(message).length > 0
}

function hasAssistantContent(message) {
  return Boolean(
    message?.explanation ||
    shouldRenderCodeDetails(message) ||
    toolActivityRows(message).length > 0 ||
    pendingIntervention(message) ||
    (SHOW_EPHEMERAL_TRACE && hasStreamTrace(message)) ||
    (Array.isArray(message?.toolEvents) && message.toolEvents.length > 0)
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
    shouldRenderCodeSnapshot(message)
  )
}

function openCodePane() {
  appStore.setActiveTab('workspace')
  appStore.setWorkspacePane('code')
}

function isEphemeralRowExpanded(rowId) {
  if (appStore.isLoading) return true
  return ephemeralExpandedRows.value.has(String(rowId))
}

function toggleEphemeralRow(rowId) {
  if (appStore.isLoading) return
  suppressMutationAutoScroll.value = true
  const key = String(rowId)
  if (ephemeralExpandedRows.value.has(key)) {
    ephemeralExpandedRows.value.delete(key)
  } else {
    ephemeralExpandedRows.value.add(key)
  }
  nextTick(() => {
    suppressMutationAutoScroll.value = false
  })
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
    ephemeralExpandedRows.value.clear()
    pendingInterventionIds.value.clear()
  }
  if (shouldAutoScroll) {
    nextTick(() => scrollToBottom())
  }
})
</script>

<style scoped>
:deep(.chat-ref-highlight) {
  color: #0369a1;
  font-style: italic;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}

:deep(.chat-markdown-content) {
  font-size: 15px;
  line-height: 1.78;
  color: var(--color-text-main);
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
}

:deep(.chat-markdown-content .chat-code-block) {
  margin: 1rem 0 1.2rem;
}

:deep(.chat-code-block),
.chat-code-block {
  border: 1px solid var(--color-border);
  border-radius: 14px;
  overflow: hidden;
  background-color: #fdfcfb;
}

:deep(.chat-code-header),
.chat-code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-border);
  background-color: #f3f3ed;
  color: #6b7280;
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
  color: #52525b;
  background-color: transparent;
  transition: background-color 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}

:deep(.chat-code-copy:hover),
.chat-code-copy:hover {
  border-color: #d4d4d8;
  background-color: #f4f4f5;
  color: #27272a;
}

:deep(.chat-code-copy:focus-visible),
.chat-code-copy:focus-visible {
  outline: none;
  border-color: #a1a1aa;
  box-shadow: 0 0 0 2px rgba(161, 161, 170, 0.2);
}

:deep(.chat-code-copy[data-copied="true"]),
.chat-code-copy[data-copied="true"] {
  border-color: #d4d4d8;
  background-color: #f4f4f5;
  color: #18181b;
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
  font-size: 14px;
  line-height: 1.62;
  background-color: #fdfcfb;
  color: #111827;
}

:deep(.chat-code-scroll code),
.chat-code-scroll code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  white-space: pre;
}

:deep(.chat-code-scroll .token.comment),
.chat-code-scroll .token.comment {
  color: #6b7280;
}

:deep(.chat-code-scroll .token.keyword),
.chat-code-scroll .token.keyword {
  color: #7c3aed;
}

:deep(.chat-code-scroll .token.string),
.chat-code-scroll .token.string {
  color: #047857;
}

:deep(.chat-code-scroll .token.number),
.chat-code-scroll .token.number {
  color: #0f766e;
}

:deep(.chat-code-scroll .token.function),
.chat-code-scroll .token.function {
  color: #1d4ed8;
}

:deep(.chat-code-scroll .token.operator),
.chat-code-scroll .token.operator {
  color: #374151;
}
</style>
