<template>
  <div ref="chatContainer" data-chat-scroll-container class="space-y-6" style="min-height: 200px;" role="log" aria-live="polite" aria-relevant="additions" :aria-busy="appStore.isLoading">
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
          <p class="text-sm whitespace-pre-wrap" style="color: var(--color-text-main);">{{ message.question }}</p>
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
      <div v-if="message.explanation" class="w-full group">
        <div class="px-4 py-3 rounded-2xl rounded-tl-sm" style="background-color: transparent">
          <div class="text-sm leading-relaxed prose prose-sm max-w-none prose-pre:overflow-x-auto prose-pre:break-words" style="color: var(--color-text-main);">
            <div v-html="renderMarkdown(message.explanation)"></div>
          </div>
          <details v-if="message.toolEvents && message.toolEvents.length" class="mt-3 rounded p-2" style="border: 1px solid var(--color-border);">
            <summary class="text-xs cursor-pointer" style="color: var(--color-text-muted);">Tool and node details</summary>
            <pre class="text-xs whitespace-pre-wrap mt-2" style="color: var(--color-text-main);">{{ formatToolEvents(message.toolEvents) }}</pre>
          </details>
        </div>
        <div class="flex items-center justify-end mt-1 px-4">
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

    <!-- Sentinel for auto-scroll -->
    <div ref="end" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import {
  DocumentDuplicateIcon
} from '@heroicons/vue/24/outline'
import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'
import DOMPurify from 'dompurify'
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
const end = ref(null)
let shouldAutoScroll = true
let mutationObserver = null

const lastMessageId = computed(() => appStore.chatHistory.at(-1)?.id)

const SCROLL_THRESHOLD_PX = 100

// Markdown parser
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true
})
md.use(markdownItKatex)

// Initialize shouldAutoScroll and setup listeners on mount
onMounted(() => {
  shouldAutoScroll = true // Start with auto-scroll enabled

  // Listen for scroll events on the scrollable container
  if (chatContainer.value) {
    chatContainer.value.addEventListener('scroll', handleScroll, { passive: true })
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
})

// Clean up event listener and observer when component unmounts
onUnmounted(() => {
  if (chatContainer.value) {
    chatContainer.value.removeEventListener('scroll', handleScroll)
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
  return DOMPurify.sanitize(html)
}

function formatToolEvents(events) {
  try {
    return JSON.stringify(events, null, 2)
  } catch (_error) {
    return String(events)
  }
}

async function loadMoreTurns() {
  try {
    await appStore.fetchConversationTurns({ reset: false })
  } catch (error) {
    console.error('Failed to load more turns:', error)
  }
}

function isNearBottom() {
  if (!chatContainer.value) return true

  const container = chatContainer.value
  const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
  return distanceFromBottom < SCROLL_THRESHOLD_PX
}

function scrollToBottom() {
  if (!end.value) return

  nextTick(() => {
    const behavior = appStore.isLoading ? 'auto' : 'smooth'
    end.value.scrollIntoView({ behavior, block: 'end' })
  })
}

function handleScroll() {
  shouldAutoScroll = isNearBottom()
}

// Watch for chat history changes and auto-scroll if user is near bottom
watch([() => appStore.chatHistory.length, lastMessageId], ([newLength], [oldLength]) => {
  if (shouldAutoScroll && newLength > oldLength) {
    nextTick(() => scrollToBottom())
  }
})

// Watch for loading state changes
watch(() => appStore.isLoading, (isLoading) => {
  if (shouldAutoScroll) {
    nextTick(() => scrollToBottom())
  }
})
</script>
