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
          <MagnifyingGlassIcon class="h-4 w-4" />
        </div>
        <div class="min-w-0 flex-1">
          <h3 id="command-palette-title" class="truncate text-sm font-semibold text-[var(--color-text-main)]">Command Palette</h3>
          <p class="truncate text-[12px] text-[var(--color-text-muted)]">Run commands or switch conversations across workspaces.</p>
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
            placeholder="Search commands, conversations, or workspaces"
            aria-label="Search commands and conversations"
          />
        </label>
      </div>

      <div class="min-h-[18rem] overflow-y-auto px-2 py-2">
        <div v-if="filteredCommandActions.length > 0" class="pb-2">
          <p class="command-palette-section-label">Commands</p>
          <button
            v-for="(row, index) in filteredCommandActions"
            :key="row.id"
            type="button"
            class="command-palette-row"
            :class="[
              index === activeIndex ? 'command-palette-row-highlighted' : '',
              row.disabled ? 'command-palette-row-disabled' : '',
            ]"
            :disabled="row.disabled || Boolean(commandActionBusyId)"
            @mouseenter="activeIndex = index"
            @click="runCommandAction(row)"
          >
            <span class="command-palette-action-icon">
              <component :is="row.icon" class="h-4 w-4" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex min-w-0 items-center gap-2">
                <span class="truncate text-[13px] font-semibold text-[var(--color-text-main)]">{{ row.title }}</span>
                <span v-if="row.statusLabel" class="command-palette-pill">{{ row.statusLabel }}</span>
              </span>
              <span class="mt-1 block truncate text-[11px] text-[var(--color-text-muted)]">{{ row.subtitle }}</span>
            </span>
            <ArrowPathIcon v-if="commandActionBusyId === row.id" class="h-4 w-4 shrink-0 animate-spin text-[var(--color-text-muted)]" />
          </button>
        </div>

        <div v-if="loading" class="flex h-32 items-center justify-center gap-2 text-[13px] text-[var(--color-text-muted)]">
          <ArrowPathIcon class="h-4 w-4 animate-spin" />
          <span>Loading conversations</span>
        </div>

        <div v-else-if="paletteRows.length === 0" class="flex h-56 items-center justify-center px-6 text-center">
          <div>
            <p class="text-sm font-medium text-[var(--color-text-main)]">No results found</p>
            <p class="mt-1 text-[12px] text-[var(--color-text-muted)]">{{ emptyStateText }}</p>
          </div>
        </div>

        <template v-else>
          <p v-if="filteredConversationRows.length > 0" class="command-palette-section-label">Conversations</p>
          <button
            v-for="(row, index) in filteredConversationRows"
            :key="`${row.workspaceId}:${row.id}`"
            type="button"
            class="command-palette-row"
            :class="[
              row.id === appStore.activeConversationId ? 'command-palette-row-active' : '',
              conversationStartIndex + index === activeIndex ? 'command-palette-row-highlighted' : '',
            ]"
            :disabled="Boolean(selectingConversationId)"
            @mouseenter="activeIndex = conversationStartIndex + index"
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
  CircleStackIcon,
  Cog6ToothIcon,
  CommandLineIcon,
  FolderOpenIcon,
  ListBulletIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  RectangleGroupIcon,
  ShareIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { formatCompactRelativeTimestamp, formatExactTimestamp, parseTimestamp } from '../../utils/dateUtils'
import { SHORTCUTS, shortcutLabel } from '../../utils/keyboardShortcuts'
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
const commandActionBusyId = ref('')
const searchInputRef = ref(null)
const conversationsByWorkspace = ref({})
let loadRequestId = 0

const normalizedQuery = computed(() => String(query.value || '').trim().toLowerCase())
const platform = typeof navigator !== 'undefined' ? navigator.platform : ''

const workspaceItems = computed(() => (
  Array.isArray(appStore.workspaces) ? appStore.workspaces : []
))

function shortcutText(shortcutId) {
  const shortcut = SHORTCUTS.find((item) => item.id === shortcutId)
  return shortcut ? shortcutLabel(shortcut, platform) : ''
}

const commandActions = computed(() => [
  {
    type: 'action',
    id: 'open-settings',
    title: 'Open Settings',
    subtitle: 'LLM, workspace, account, appearance, and preferences.',
    keywords: 'settings preferences api llm account appearance theme workspace',
    statusLabel: shortcutText('settings'),
    icon: Cog6ToothIcon,
    run: () => {
      emit('close')
      appStore.openSettings('llm')
    },
  },
  {
    type: 'action',
    id: 'show-shortcuts',
    title: 'Show Keyboard Shortcuts',
    subtitle: 'Review all global shortcuts available in this workspace.',
    keywords: 'keyboard shortcuts help commands',
    statusLabel: '',
    icon: ListBulletIcon,
    run: () => {
      emit('close')
      appStore.openKeyboardShortcuts()
    },
  },
  {
    type: 'action',
    id: 'toggle-sidebar',
    title: appStore.isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar',
    subtitle: 'Show or hide the workspace sidebar.',
    keywords: 'sidebar navigation collapse expand',
    statusLabel: shortcutText('sidebar'),
    icon: RectangleGroupIcon,
    run: () => {
      appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
      emit('close')
    },
  },
  {
    type: 'action',
    id: 'toggle-terminal',
    title: appStore.isTerminalOpen ? 'Close Terminal' : 'Open Terminal',
    subtitle: 'Toggle the terminal panel.',
    keywords: 'terminal shell console command line',
    statusLabel: shortcutText('terminal'),
    icon: CommandLineIcon,
    run: () => {
      appStore.toggleTerminal()
      emit('close')
    },
  },
  {
    type: 'action',
    id: 'open-schema',
    title: 'Open Schema',
    subtitle: 'Inspect tables, columns, aliases, and schema metadata.',
    keywords: 'schema tables columns metadata',
    statusLabel: shortcutText('schema'),
    icon: CircleStackIcon,
    run: () => {
      appStore.setActiveTab('schema-editor')
      emit('close')
    },
  },
  {
    type: 'action',
    id: 'open-conversation-tree',
    title: 'Open Conversation Tree',
    subtitle: 'Browse turns, branches, and saved outputs.',
    keywords: 'conversation tree turns branches graph',
    statusLabel: shortcutText('conversation-tree'),
    icon: ShareIcon,
    run: () => {
      appStore.setActiveTab('conversation-tree')
      emit('close')
    },
  },
  {
    type: 'action',
    id: 'import-dataset',
    title: 'Import Dataset',
    subtitle: 'Choose CSV, TSV, Parquet, JSON, XLSX, or XLS files.',
    keywords: 'dataset import data file upload add',
    statusLabel: shortcutText('dataset-import'),
    icon: FolderOpenIcon,
    run: () => {
      emit('close')
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('inquira:open-dataset-picker'))
      }
    },
  },
  {
    type: 'action',
    id: 'new-conversation',
    title: 'New Conversation',
    subtitle: appStore.hasWorkspace ? 'Start a fresh conversation in the active workspace.' : 'Select or create a workspace first.',
    keywords: 'new conversation chat thread',
    statusLabel: appStore.hasWorkspace ? '' : 'Workspace required',
    icon: PencilSquareIcon,
    disabled: !appStore.hasWorkspace,
    run: createConversationFromPalette,
  },
])

const filteredCommandActions = computed(() => {
  const queryText = normalizedQuery.value
  if (!queryText) return commandActions.value
  return commandActions.value.filter((row) => (
    `${row.title} ${row.subtitle} ${row.keywords} ${row.statusLabel}`.toLowerCase().includes(queryText)
  ))
})

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
        type: 'conversation',
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

const conversationStartIndex = computed(() => filteredCommandActions.value.length)

const paletteRows = computed(() => [
  ...filteredCommandActions.value,
  ...filteredConversationRows.value,
])

const emptyStateText = computed(() => (
  normalizedQuery.value
    ? 'Try a different command, title, or workspace name.'
    : 'Create a conversation from the sidebar or the New Conversation command.'
))

const footerLabel = computed(() => {
  const commandCount = filteredCommandActions.value.length
  const conversationCount = filteredConversationRows.value.length
  const commandSuffix = commandCount === 1 ? 'command' : 'commands'
  const conversationSuffix = conversationCount === 1 ? 'conversation' : 'conversations'
  return `${commandCount} ${commandSuffix} · ${conversationCount} ${conversationSuffix}`
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

async function createConversationFromPalette() {
  if (!appStore.hasWorkspace) return
  const conversation = await appStore.createConversation()
  if (conversation?.id) {
    appStore.setActiveConversationId(conversation.id)
  }
  appStore.setWorkspacePane('chat')
  appStore.setActiveTab('workspace')
  await appStore.fetchConversationTurns({ reset: true })
  emit('close')
}

async function runCommandAction(row) {
  if (!row?.run || row.disabled || commandActionBusyId.value) return
  commandActionBusyId.value = row.id
  try {
    await row.run()
  } catch (error) {
    toast.error('Command Failed', extractApiErrorMessage(error, `Failed to run ${row.title}`))
  } finally {
    commandActionBusyId.value = ''
  }
}

function moveActiveIndex(step) {
  const total = paletteRows.value.length
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
    const row = paletteRows.value[activeIndex.value]
    if (!row) return
    event.preventDefault()
    if (row.type === 'action') {
      void runCommandAction(row)
      return
    }
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

watch(paletteRows, (rows) => {
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

.command-palette-row-disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.command-palette-section-label {
  color: var(--color-text-muted);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 0.375rem 0.75rem 0.25rem;
  text-transform: uppercase;
}

.command-palette-action-icon {
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  display: inline-flex;
  flex-shrink: 0;
  height: 2rem;
  justify-content: center;
  width: 2rem;
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
