<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-[95] flex items-start justify-center px-4 pt-[9vh]"
    role="dialog"
    aria-modal="true"
    aria-labelledby="command-palette-title"
  >
    <div class="modal-overlay" @click="emit('close')"></div>
    <div class="modal-card command-palette-card relative flex w-full max-w-3xl flex-col overflow-hidden" @click.stop @keydown="handlePaletteKeydown">
      <div class="flex items-center gap-3 border-b border-[var(--color-border)] px-4 py-3">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[var(--color-selected-surface)] text-[var(--color-text-main)]">
          <CommandLineIcon class="h-4 w-4" />
        </div>
        <div class="min-w-0 flex-1">
          <h3 id="command-palette-title" class="truncate text-sm font-semibold text-[var(--color-text-main)]">Command Palette</h3>
          <p class="truncate text-[12px] text-[var(--color-text-muted)]">Switch conversations across workspaces.</p>
        </div>
        <button type="button" class="btn-icon h-8 w-8" aria-label="Close command palette" @click="emit('close')">
          <XMarkIcon class="h-4 w-4" />
        </button>
      </div>

      <div class="border-b border-[var(--color-border)] px-4 py-3">
        <label class="relative block">
          <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            ref="searchInputRef"
            v-model="query"
            type="search"
            class="command-palette-search"
            placeholder="Search conversations or workspaces"
            aria-label="Search conversations"
          />
        </label>
      </div>

      <div class="min-h-[18rem] overflow-y-auto px-2 py-2">
        <div v-if="loading" class="flex h-56 items-center justify-center gap-2 text-[13px] text-[var(--color-text-muted)]">
          <ArrowPathIcon class="h-4 w-4 animate-spin" />
          <span>Loading conversations</span>
        </div>

        <div v-else-if="filteredConversationRows.length === 0" class="flex h-56 items-center justify-center px-6 text-center">
          <div>
            <p class="text-sm font-medium text-[var(--color-text-main)]">No conversations found</p>
            <p class="mt-1 text-[12px] text-[var(--color-text-muted)]">{{ emptyStateText }}</p>
          </div>
        </div>

        <template v-else>
          <button
            v-for="(row, index) in filteredConversationRows"
            :key="`${row.workspaceId}:${row.id}`"
            type="button"
            class="command-palette-row"
            :class="[
              row.id === appStore.activeConversationId ? 'command-palette-row-active' : '',
              index === activeIndex ? 'command-palette-row-highlighted' : '',
            ]"
            :disabled="Boolean(selectingConversationId)"
            @mouseenter="activeIndex = index"
            @click="selectConversation(row)"
          >
            <span class="command-palette-initials" :title="row.workspaceName">{{ workspaceInitials(row.workspaceName) }}</span>
            <span class="min-w-0 flex-1">
              <span class="flex min-w-0 items-center gap-2">
                <span class="truncate text-[13px] font-semibold text-[var(--color-text-main)]">{{ row.title }}</span>
                <span v-if="row.id === appStore.activeConversationId" class="command-palette-pill command-palette-pill-active">Active</span>
                <span class="command-palette-pill" :class="row.isRunning ? 'command-palette-pill-running' : ''">
                  {{ row.statusLabel }}
                </span>
              </span>
              <span class="mt-1 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[var(--color-text-muted)]">
                <span class="truncate">{{ row.workspaceName }}</span>
                <span :title="row.createdTitle">{{ row.createdLabel }}</span>
                <span v-if="row.lastActiveLabel" :title="row.lastActiveTitle">{{ row.lastActiveLabel }}</span>
              </span>
            </span>
            <CheckIcon v-if="row.id === appStore.activeConversationId" class="h-4 w-4 shrink-0 text-[var(--color-accent)]" />
          </button>
        </template>
      </div>

      <div class="flex items-center justify-between gap-3 border-t border-[var(--color-border)] px-4 py-2 text-[11px] text-[var(--color-text-muted)]">
        <span>{{ footerLabel }}</span>
        <span v-if="loadError" class="truncate text-[var(--color-warning)]">{{ loadError }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  ArrowPathIcon,
  CheckIcon,
  CommandLineIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { formatCompactRelativeTimestamp, formatExactTimestamp, parseTimestamp } from '../../utils/dateUtils'
import { workspaceInitials } from '../../utils/workspaceDisplay'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const appStore = useAppStore()
const query = ref('')
const loading = ref(false)
const loadError = ref('')
const activeIndex = ref(0)
const selectingConversationId = ref('')
const searchInputRef = ref(null)
const conversationsByWorkspace = ref({})
let loadRequestId = 0

const normalizedQuery = computed(() => String(query.value || '').trim().toLowerCase())

const workspaceItems = computed(() => (
  Array.isArray(appStore.workspaces) ? appStore.workspaces : []
))

const allConversationRows = computed(() => {
  const rows = []
  for (const workspace of workspaceItems.value) {
    const workspaceId = String(workspace?.id || '').trim()
    if (!workspaceId) continue
    const conversations = Array.isArray(conversationsByWorkspace.value?.[workspaceId])
      ? conversationsByWorkspace.value[workspaceId]
      : (workspaceId === String(appStore.activeWorkspaceId || '').trim() && Array.isArray(appStore.conversations) ? appStore.conversations : [])
    const workspaceName = String(workspace?.name || 'Untitled workspace').trim() || 'Untitled workspace'

    for (const conversation of conversations) {
      const id = String(conversation?.id || '').trim()
      if (!id) continue
      const createdAt = conversation?.created_at
      const lastActiveAt = conversationTimestampValue(conversation)
      const run = appStore.getConversationRun(id)
      const isRunning = appStore.isConversationRunning(id)
      rows.push({
        id,
        workspaceId,
        workspaceName,
        title: String(conversation?.title || 'Untitled conversation').trim() || 'Untitled conversation',
        createdAt,
        createdLabel: formatCreatedLabel(createdAt),
        createdTitle: formatExactTimestamp(createdAt),
        lastActiveAt,
        lastActiveLabel: formatLastActiveLabel(lastActiveAt),
        lastActiveTitle: formatExactTimestamp(lastActiveAt),
        isRunning,
        statusLabel: isRunning ? (String(run?.message || '').trim() || 'Running') : 'Idle',
        timestampMs: timestampMs(lastActiveAt || createdAt),
      })
    }
  }

  return rows.sort((left, right) => {
    if (left.isRunning !== right.isRunning) return left.isRunning ? -1 : 1
    return right.timestampMs - left.timestampMs
  })
})

const filteredConversationRows = computed(() => {
  const queryText = normalizedQuery.value
  if (!queryText) return allConversationRows.value
  return allConversationRows.value.filter((row) => (
    `${row.title} ${row.workspaceName} ${row.statusLabel}`.toLowerCase().includes(queryText)
  ))
})

const emptyStateText = computed(() => (
  normalizedQuery.value
    ? 'Try a different title or workspace name.'
    : 'Create a conversation from the chat header or sidebar.'
))

const footerLabel = computed(() => {
  const total = filteredConversationRows.value.length
  const suffix = total === 1 ? 'conversation' : 'conversations'
  return `${total} ${suffix}`
})

function conversationTimestampValue(conversation) {
  return conversation?.last_turn_at || conversation?.updated_at || conversation?.created_at
}

function timestampMs(value) {
  const date = parseTimestamp(value)
  return date ? date.getTime() : 0
}

function formatCreatedLabel(value) {
  const exact = formatExactTimestamp(value)
  return exact === 'No date available' ? 'Created date unavailable' : `Created ${exact}`
}

function formatLastActiveLabel(value) {
  const label = formatCompactRelativeTimestamp(value)
  return label ? `Last active ${label}` : ''
}

async function loadConversations() {
  const requestId = ++loadRequestId
  loading.value = true
  loadError.value = ''
  try {
    if (workspaceItems.value.length === 0) {
      await appStore.fetchWorkspaces()
    }
    const workspaces = workspaceItems.value
    const entries = {}
    let failedCount = 0
    await Promise.all(workspaces.map(async (workspace) => {
      const workspaceId = String(workspace?.id || '').trim()
      if (!workspaceId) return
      try {
        const response = await apiService.v1ListConversations(workspaceId, 200)
        entries[workspaceId] = Array.isArray(response?.conversations) ? response.conversations : []
      } catch (_error) {
        failedCount += 1
        entries[workspaceId] = workspaceId === String(appStore.activeWorkspaceId || '').trim() && Array.isArray(appStore.conversations)
          ? appStore.conversations
          : []
      }
    }))
    if (requestId !== loadRequestId) return
    conversationsByWorkspace.value = entries
    if (failedCount > 0) {
      loadError.value = failedCount === 1 ? 'One workspace could not be loaded.' : `${failedCount} workspaces could not be loaded.`
    }
  } finally {
    if (requestId === loadRequestId) {
      loading.value = false
    }
  }
}

async function selectConversation(row) {
  if (!row?.id || selectingConversationId.value) return
  selectingConversationId.value = row.id
  try {
    if (row.workspaceId !== String(appStore.activeWorkspaceId || '').trim()) {
      await appStore.activateWorkspace(row.workspaceId)
      await appStore.fetchConversations()
    } else if (!Array.isArray(appStore.conversations) || appStore.conversations.length === 0) {
      await appStore.fetchConversations()
    }
    appStore.setActiveConversationId(row.id)
    appStore.setWorkspacePane('chat')
    appStore.setActiveTab('workspace')
    await appStore.fetchConversationTurns({ reset: true, preferLatest: true })
    emit('close')
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to load conversation'))
  } finally {
    selectingConversationId.value = ''
  }
}

function moveActiveIndex(step) {
  const total = filteredConversationRows.value.length
  if (total === 0) return
  activeIndex.value = (activeIndex.value + step + total) % total
}

function handlePaletteKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActiveIndex(1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActiveIndex(-1)
    return
  }
  if (event.key === 'Enter') {
    const row = filteredConversationRows.value[activeIndex.value]
    if (!row) return
    event.preventDefault()
    void selectConversation(row)
  }
}

watch(() => props.isOpen, async (open) => {
  if (!open) return
  query.value = ''
  activeIndex.value = 0
  await nextTick()
  searchInputRef.value?.focus?.()
  void loadConversations()
})

watch(filteredConversationRows, (rows) => {
  if (activeIndex.value >= rows.length) {
    activeIndex.value = Math.max(0, rows.length - 1)
  }
})
</script>

<style scoped>
.command-palette-card {
  background: var(--color-panel-elevated);
  box-shadow: var(--shadow-modal);
}

.command-palette-search {
  min-height: 2.5rem;
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-base);
  color: var(--color-text-main);
  font-size: 0.875rem;
  outline: none;
  padding: 0 0.75rem 0 2.25rem;
  transition:
    border-color var(--motion-duration-standard) var(--motion-ease-standard),
    box-shadow var(--motion-duration-standard) var(--motion-ease-standard);
}

.command-palette-search::placeholder {
  color: var(--color-text-muted);
}

.command-palette-search:focus {
  border-color: var(--color-selected-border);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent) 14%, transparent);
}

.command-palette-row {
  align-items: center;
  border-radius: var(--radius-md);
  color: var(--color-text-main);
  display: flex;
  gap: 0.75rem;
  min-height: 4rem;
  padding: 0.625rem 0.75rem;
  text-align: left;
  width: 100%;
  transition:
    background-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard);
}

.command-palette-row:hover,
.command-palette-row-highlighted {
  background: color-mix(in srgb, var(--color-text-main) 6%, transparent);
}

.command-palette-row-active {
  background: var(--color-selected-surface);
}

.command-palette-initials {
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-main);
  display: inline-flex;
  flex-shrink: 0;
  font-size: 0.6875rem;
  font-weight: 800;
  height: 2rem;
  justify-content: center;
  letter-spacing: 0.02em;
  width: 2rem;
}

.command-palette-pill {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  color: var(--color-text-muted);
  flex-shrink: 0;
  font-size: 0.625rem;
  font-weight: 700;
  line-height: 1;
  padding: 0.1875rem 0.4375rem;
}

.command-palette-pill-active {
  border-color: var(--color-selected-border);
  color: var(--color-accent);
}

.command-palette-pill-running {
  border-color: color-mix(in srgb, var(--color-warning) 42%, var(--color-border));
  color: var(--color-warning);
}
</style>
