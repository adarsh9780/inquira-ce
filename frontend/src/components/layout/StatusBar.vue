<template>
  <div class="status-bar h-7 w-full bg-[var(--color-surface)] border-t border-[var(--color-border)] flex items-center justify-between px-3 text-[11px] font-normal text-[var(--color-text-muted)] select-none z-50 shrink-0">

    <!-- Left Section: Token usage, runtime status, and editor position -->
    <div class="flex items-center gap-3 h-full">
      <div
        v-if="authStore.isAuthenticated && hasTokenUsage"
        class="flex items-center gap-1 h-full px-1 tabular-nums text-[var(--color-text-muted)]"
        :title="tokenUsageHoverLabel"
      >
        <span class="truncate">{{ tokenUsageSummaryLabel }}</span>
      </div>

      <div v-if="appStore.activeWorkspaceId" class="flex h-full items-center gap-1.5 px-1">
        <span
          v-if="workspaceRuntimeStatusMeta.showSpinner"
          class="inline-block h-2 w-2 shrink-0 animate-spin rounded-full border-[1.5px] border-[var(--color-border)] border-t-[var(--color-text-main)]"
          aria-hidden="true"
        ></span>
        <span v-else class="h-2 w-2 shrink-0 rounded-full" :class="workspaceRuntimeStatusMeta.dotClass"></span>
        <span class="font-medium" :class="workspaceRuntimeStatusMeta.textClass">
          Engine {{ workspaceRuntimeStatusMeta.label.toLowerCase() }}
        </span>
      </div>

      <template v-if="appStore.isEditorFocused">
        <div class="w-px h-3.5 bg-[var(--color-border)]"></div>
        <div class="flex items-center tabular-nums text-[var(--color-text-muted)] tracking-tight gap-1 px-1">
          <span>Ln {{ appStore.editorLine }},</span>
          <span>Col {{ appStore.editorCol }}</span>
        </div>
      </template>
    </div>

    <!-- Center Section: Data pane status -->
    <div class="flex items-center gap-2 h-full">
      <!-- Data pane error takes priority -->
      <template v-if="appStore.dataPaneError">
        <div class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-[var(--color-error)]/10 text-[var(--color-error)] max-w-[280px] truncate"
             :title="appStore.dataPaneError">
          <span class="w-1.5 h-1.5 rounded-full bg-[var(--color-error)] shrink-0"></span>
          <span class="truncate">{{ appStore.dataPaneError }}</span>
        </div>
      </template>
      <template v-else>
        <div
          v-if="primaryBackgroundOperation"
          class="flex max-w-[360px] items-center gap-1.5 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 font-medium tabular-nums text-[var(--color-text-muted)]"
          :title="primaryBackgroundOperationTitle"
          data-background-operation-status
        >
          <span
            v-if="primaryBackgroundOperationIsRunning"
            class="inquira-spinner h-2.5 w-2.5 shrink-0 border-[1.5px]"
            aria-hidden="true"
          ></span>
          <span
            v-else
            class="h-2 w-2 shrink-0 rounded-full"
            :class="primaryBackgroundOperation.status === 'failed' ? 'bg-[var(--color-error)]' : 'bg-[var(--color-success)]'"
          ></span>
          <span class="truncate">{{ primaryBackgroundOperationLabel }}</span>
          <span v-if="backgroundOperationCountLabel" class="shrink-0 text-[var(--color-text-sub)]">{{ backgroundOperationCountLabel }}</span>
        </div>
        <div v-if="appStore.activeWorkspaceId && paneArtifactCountLabel" class="flex items-center gap-1.5 px-2 py-0.5 rounded font-medium tabular-nums"
             :class="artifactCountClass">
          <span>{{ paneArtifactCountLabel }}</span>
        </div>
        <div v-if="appStore.activeWorkspaceId && tableViewportLabel" class="flex items-center gap-1.5 px-2 py-0.5 rounded font-medium tabular-nums" :class="artifactCountClass">
          <span>{{ tableViewportLabel }}</span>
        </div>
      </template>
    </div>

    <!-- Right Section: Terminal and alerts -->
    <div class="flex items-center gap-3 h-full">
      <!-- Terminal Toggle -->
      <button
        @click="appStore.toggleTerminal()"
        class="flex items-center gap-1.5 h-full px-1.5 text-[11px] font-medium hover:bg-[var(--color-base)] transition-colors"
        :class="appStore.isTerminalOpen ? 'text-[var(--color-accent)] font-medium' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
        title="Toggle terminal panel (Cmd/Ctrl+J)"
      >
        <CommandLineIcon class="w-3.5 h-3.5" />
        <span>Terminal</span>
      </button>

      <div class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <div class="relative" data-notification-center>
        <button
          type="button"
          class="relative flex items-center gap-1.5 h-full px-1.5 text-[11px] font-medium hover:bg-[var(--color-base)] transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]"
          title="Session notifications"
          aria-haspopup="true"
          :aria-expanded="notificationsPanelOpen"
          @click="toggleNotificationsPanel"
        >
          <BellIcon class="w-3.5 h-3.5" />
          <span>Alerts</span>
          <span
            v-if="unreadNotificationCount > 0"
            class="absolute -right-0.5 -top-0.5 inline-flex min-w-[1rem] items-center justify-center rounded-full px-1 text-[9px] font-semibold leading-4 text-[var(--color-on-accent)]"
            style="background-color: var(--color-error);"
          >
            {{ unreadNotificationBadge }}
          </span>
        </button>

        <Transition name="motion-popover">
        <div
          v-if="notificationsPanelOpen"
          class="motion-popover-surface motion-popover-from-bottom layer-modal-dropdown absolute right-0 bottom-full mb-2 w-[24rem] overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-[var(--shadow-lifted)]"
        >
          <div class="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
            <div>
              <p class="text-sm font-semibold text-[var(--color-text-main)]">Session Notifications</p>
              <p class="text-[11px] text-[var(--color-text-muted)]">Stored for this app session only.</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="text-[11px] font-medium text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)]"
                @click="clearNotificationHistory"
              >
                Clear
              </button>
              <button
                type="button"
                class="text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)]"
                title="Close notifications"
                aria-label="Close notifications"
                @click="closeNotificationsPanel"
              >
                <XMarkIcon class="h-4 w-4" />
              </button>
            </div>
          </div>

          <div v-if="notificationHistory.length === 0" class="px-4 py-6 text-sm text-[var(--color-text-muted)]">
            No notifications in this session yet.
          </div>
          <div v-else class="max-h-80 overflow-y-auto">
            <div
              v-for="entry in notificationHistory"
              :key="entry.id"
              class="border-b border-[var(--color-border)] px-4 py-3 last:border-b-0"
              :style="{ backgroundColor: entry.read ? 'transparent' : 'color-mix(in srgb, var(--color-accent) 5%, var(--color-base))' }"
            >
              <div class="flex items-start gap-3">
                <span class="mt-1 inline-flex h-2 w-2 shrink-0 rounded-full" :class="notificationDotClass(entry.type)"></span>
                <div class="min-w-0 flex-1">
                  <div class="flex items-start justify-between gap-3">
                    <p class="text-[12px] font-semibold text-[var(--color-text-main)]">{{ entry.title }}</p>
                    <span class="shrink-0 text-[10px] text-[var(--color-text-muted)]">{{ formatNotificationTimestamp(entry.createdAt) }}</span>
                  </div>
                  <p v-if="entry.message" class="mt-1 whitespace-pre-wrap break-words text-[11px] leading-5 text-[var(--color-text-muted)]">
                    {{ entry.message }}
                  </p>
                  <div class="mt-2 flex items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
                    <span v-if="entry.source">{{ entry.source }}</span>
                    <span v-if="entry.statusCode">HTTP {{ entry.statusCode }}</span>
                    <span class="uppercase tracking-[0.08em]">{{ entry.type }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        </Transition>
      </div>

    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import apiService from '../../services/apiService'
import { formatUsageCompact, formatUsageTooltip, normalizeUsage } from '../../utils/usageFormat'
import {
  BellIcon,
  CommandLineIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useToast } from '../../composables/useToast'

const appStore = useAppStore()
const authStore = useAuthStore()
const {
  notificationHistory,
  unreadNotificationCount,
  markAllNotificationsRead,
  clearNotificationHistory,
} = useToast()

// --- Workspace Status Management ---
const workspaceRuntimeStatus = computed(() => appStore.activeWorkspaceRuntimeStatus)

const notificationsPanelOpen = ref(false)

const unreadNotificationBadge = computed(() => {
  const count = Number(unreadNotificationCount.value || 0)
  if (count <= 0) return ''
  return count > 99 ? '99+' : String(count)
})

const tokenUsageSource = computed(() => {
  const summary = appStore.activeConversationUsage && typeof appStore.activeConversationUsage === 'object'
    ? appStore.activeConversationUsage
    : null
  return summary?.usage || appStore.liveTokenUsage
})

const hasTokenUsage = computed(() => Boolean(normalizeUsage(tokenUsageSource.value)))

const tokenUsageSummaryLabel = computed(() => formatUsageCompact(tokenUsageSource.value))

const tokenUsageHoverLabel = computed(() => {
  const summary = appStore.activeConversationUsage && typeof appStore.activeConversationUsage === 'object'
    ? appStore.activeConversationUsage
    : null
  return formatUsageTooltip(tokenUsageSource.value, summary)
})

const primaryBackgroundOperation = computed(() => appStore.primaryBackgroundOperation)

const primaryBackgroundOperationIsRunning = computed(() => {
  const status = String(primaryBackgroundOperation.value?.status || '')
  return status === 'queued' || status === 'running'
})

const backgroundOperationCountLabel = computed(() => {
  const count = Number(appStore.activeBackgroundOperations?.length || 0)
  return count > 1 ? `+${count - 1}` : ''
})

const primaryBackgroundOperationLabel = computed(() => {
  const runningChats = Number(appStore.runningConversationCount || 0)
  if (runningChats > 1) return `${runningChats} conversations running`
  const operation = primaryBackgroundOperation.value
  if (!operation) return ''
  const message = String(operation.message || operation.title || '').trim()
  const progress = Number(operation.progress)
  if (Number.isFinite(progress)) {
    return `${message} ${Math.round(progress)}%`
  }
  return message
})

const primaryBackgroundOperationTitle = computed(() => {
  const operation = primaryBackgroundOperation.value
  if (!operation) return ''
  const title = String(operation.title || 'Background task').trim()
  const message = String(operation.message || '').trim()
  const count = Number(appStore.activeBackgroundOperations?.length || 0)
  return [
    title,
    message,
    count > 1 ? `${count} background tasks active` : '',
  ].filter(Boolean).join('\n')
})

function runtimeStatusMeta(status) {
  switch (status) {
    case 'ready':
      return { dotClass: 'bg-[var(--color-success)]', textClass: 'text-[var(--color-success)]', label: 'Ready', showSpinner: false }
    case 'busy':
      return { dotClass: 'bg-[var(--color-warning)]', textClass: 'text-[var(--color-warning)]', label: 'Working', showSpinner: false }
    case 'starting':
    case 'connecting':
      return { dotClass: 'bg-[var(--color-accent)]', textClass: 'text-[var(--color-accent)]', label: 'Starting', showSpinner: true }
    case 'error':
      return { dotClass: 'bg-[var(--color-error)]', textClass: 'text-[var(--color-error)]', label: 'Needs attention', showSpinner: false }
    case 'missing':
    default:
      return { dotClass: 'bg-[var(--color-text-muted)]', textClass: 'text-[var(--color-text-muted)]', label: 'Idle', showSpinner: false }
  }
}

const workspaceRuntimeStatusMeta = computed(() => {
  return runtimeStatusMeta(workspaceRuntimeStatus.value)
})

const tableViewportLabel = computed(() => {
  if (appStore.dataPane !== 'table') return null
  const total = Number(appStore.tableRowCount || 0)
  if (total <= 0) return null
  const start = Math.max(0, Number(appStore.tableWindowStart || 0))
  const end = Math.max(0, Number(appStore.tableWindowEnd || 0))
  if (start > 0 && end > 0) {
    return `${total.toLocaleString()} rows - Showing ${start.toLocaleString()}-${end.toLocaleString()} of ${total.toLocaleString()}`
  }
  return `${total.toLocaleString()} rows`
})

// Tab-aware artifact count for the currently visible data pane.
const paneArtifactCountLabel = computed(() => {
  if (appStore.dataPane === 'table') {
    const n = Math.max(
      Number(appStore.dataframeCount || 0),
      Number(Array.isArray(appStore.dataframes) ? appStore.dataframes.length : 0)
    )
    if (n <= 0) return null
    return `${n} table${n === 1 ? '' : 's'} saved`
  }
  if (appStore.dataPane === 'figure') {
    const n = Math.max(
      Number(appStore.figureCount || 0),
      Number(Array.isArray(appStore.figures) ? appStore.figures.length : 0)
    )
    if (n <= 0) return null
    return `${n} chart${n === 1 ? '' : 's'} saved`
  }
  return null
})

const artifactCountClass = computed(() => {
  // Neutral metadata badge — informational, not an accent action.
  return 'bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)]'
})

async function refreshWorkspaceRuntimeStatusFromApi(workspaceId, fallbackStatus = 'missing') {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return 'missing'
  try {
    const payload = await apiService.v1GetWorkspaceRuntimeStatus(normalizedWorkspaceId)
    const status = String(payload?.status || '').trim().toLowerCase() || fallbackStatus
    appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, status)
    return status
  } catch (_error) {
    appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, fallbackStatus)
    return fallbackStatus
  }
}

function formatNotificationTimestamp(value) {
  const timestamp = Number(value || 0)
  if (!Number.isFinite(timestamp) || timestamp <= 0) return ''
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function notificationDotClass(type) {
  if (type === 'success') return 'bg-[var(--color-success)]'
  if (type === 'error') return 'bg-[var(--color-error)]'
  if (type === 'warning') return 'bg-[var(--color-warning)]'
  return 'bg-[var(--color-info)]'
}

function openNotificationsPanel() {
  notificationsPanelOpen.value = true
  markAllNotificationsRead()
}

function closeNotificationsPanel() {
  notificationsPanelOpen.value = false
}

function toggleNotificationsPanel() {
  if (notificationsPanelOpen.value) {
    closeNotificationsPanel()
    return
  }
  openNotificationsPanel()
}

function handleGlobalPointerDown(event) {
  const target = event?.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-notification-center]')) return
  closeNotificationsPanel()
}

function handleStatusBarEscape(event) {
  if (event.key === 'Escape') {
    closeNotificationsPanel()
  }
}

function syncWorkspaceStatus() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!authStore.isAuthenticated || !workspaceId || !appStore.hasWorkspace) {
    appStore.setWorkspaceRuntimeStatus(workspaceId, 'missing')
    return
  }

  const currentStatus = appStore.getWorkspaceRuntimeStatus(workspaceId)
  void refreshWorkspaceRuntimeStatusFromApi(workspaceId, currentStatus)
}

// Named handler so we can remove the exact same reference on unmount
function handleVisibilityChange() {
  if (!document.hidden && authStore.isAuthenticated && appStore.activeWorkspaceId && appStore.hasWorkspace) {
    syncWorkspaceStatus()
  }
}

// Lifecycle and Watchers
onMounted(() => {
  syncWorkspaceStatus()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  document.addEventListener('pointerdown', handleGlobalPointerDown)
  document.addEventListener('keydown', handleStatusBarEscape)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  document.removeEventListener('pointerdown', handleGlobalPointerDown)
  document.removeEventListener('keydown', handleStatusBarEscape)
})

watch([() => appStore.activeWorkspaceId, () => appStore.hasWorkspace, () => authStore.isAuthenticated], ([newId, hasWorkspace, isAuthenticated]) => {
  const normalizedWorkspaceId = String(newId || '').trim()
  if (isAuthenticated && newId && hasWorkspace) {
    syncWorkspaceStatus()
  } else {
    appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, 'missing')
  }
})

watch(() => authStore.isAuthenticated, (authenticated) => {
  if (authenticated) syncWorkspaceStatus()
})
</script>
