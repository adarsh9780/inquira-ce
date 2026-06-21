<template>
  <div class="h-7 w-full bg-[var(--color-surface)] border-t border-[var(--color-border)] flex items-center justify-between px-3 text-[12px] text-[var(--color-text-muted)] select-none z-50 shrink-0">

    <!-- Left Section: Token usage, runtime status, and editor position -->
    <div class="flex items-center gap-3 h-full">
      <div
        v-if="authStore.isAuthenticated"
        class="flex items-center gap-1 h-full px-1 text-[10px] text-[var(--color-text-muted)]"
        style="font-family: var(--font-mono);"
        :title="tokenUsageHoverLabel"
      >
        <span class="truncate">{{ tokenUsageSummaryLabel }}</span>
      </div>

      <div v-if="authStore.isAuthenticated" class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <div class="relative h-full" data-workspace-switcher>
        <button
          type="button"
          class="flex h-full max-w-[260px] items-center gap-1.5 px-1 text-left transition-colors hover:text-[var(--color-text-main)]"
          :title="`Active workspace: ${activeWorkspaceName}`"
          @click="toggleWorkspaceSwitcher"
        >
          <span
            v-if="workspaceRuntimeStatusMeta.showSpinner"
            class="inline-block w-2 h-2 rounded-full border-[1.5px] border-[var(--color-border)] border-t-[var(--color-text-main)] animate-spin shrink-0"
            aria-hidden="true"
          ></span>
          <span v-else class="w-2 h-2 rounded-full shrink-0" :class="workspaceRuntimeStatusMeta.dotClass"></span>
          <span class="truncate font-medium text-[var(--color-text-main)]">
            {{ activeWorkspaceName }}
          </span>
          <span class="hidden text-[10px] font-medium sm:inline" :class="workspaceRuntimeStatusMeta.textClass">
            {{ workspaceRuntimeStatusMeta.label }}
          </span>
          <ChevronUpDownIcon class="h-3.5 w-3.5 shrink-0 text-[var(--color-text-muted)]" />
        </button>

        <div
          v-if="workspaceSwitcherOpen"
          class="layer-modal-dropdown absolute left-0 bottom-full mb-2 w-72 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-[var(--shadow-lifted)]"
        >
          <div class="border-b border-[var(--color-border)] px-3 py-2">
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Workspaces</p>
          </div>
          <div v-if="appStore.workspaces.length === 0" class="px-3 py-3 text-[12px] text-[var(--color-text-muted)]">
            No workspaces yet.
          </div>
          <template v-else>
            <button
              v-for="workspace in appStore.workspaces"
              :key="workspace.id"
              type="button"
              class="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-[var(--color-panel-muted)]"
              :class="workspace.id === appStore.activeWorkspaceId ? 'bg-[var(--color-selected-surface)]' : ''"
              @click="selectWorkspaceFromStatusBar(workspace.id)"
            >
              <span class="h-2 w-2 shrink-0 rounded-full" :class="runtimeStatusMetaForWorkspace(workspace.id).dotClass"></span>
              <span class="min-w-0 flex-1 truncate text-[12px] font-medium text-[var(--color-text-main)]">
                {{ workspace.name || 'Untitled workspace' }}
              </span>
              <span class="shrink-0 text-[10px]" :class="runtimeStatusMetaForWorkspace(workspace.id).textClass">
                {{ runtimeStatusMetaForWorkspace(workspace.id).label }}
              </span>
            </button>
          </template>
        </div>
      </div>

      <template v-if="appStore.isEditorFocused">
        <div class="w-px h-3.5 bg-[var(--color-border)]"></div>
        <div class="flex items-center text-[var(--color-text-muted)] tracking-tight gap-1 px-1" style="font-family: var(--font-mono);">
          <span>Ln {{ appStore.editorLine }},</span>
          <span>Col {{ appStore.editorCol }}</span>
        </div>
      </template>
    </div>

    <!-- Center Section: Data pane status -->
    <div class="flex items-center gap-2 h-full">
      <!-- Data pane error takes priority -->
      <template v-if="appStore.dataPaneError">
        <div class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--color-error)]/10 text-[var(--color-error)] max-w-[280px] truncate"
             :title="appStore.dataPaneError">
          <span class="w-1.5 h-1.5 rounded-full bg-[var(--color-error)] shrink-0"></span>
          <span class="truncate">{{ appStore.dataPaneError }}</span>
        </div>
      </template>
      <template v-else>
        <div
          v-if="primaryBackgroundOperation"
          class="flex max-w-[360px] items-center gap-1.5 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-text-muted)]"
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
        <div v-if="appStore.activeWorkspaceId && paneArtifactCountLabel" class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium"
             :class="artifactCountClass">
          <span>{{ paneArtifactCountLabel }}</span>
        </div>
        <div v-if="appStore.activeWorkspaceId && tableViewportLabel" class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium" :class="artifactCountClass">
          <span>{{ tableViewportLabel }}</span>
        </div>
        <div
          v-if="showArtifactUsageWarning"
          class="flex items-center px-1.5 py-0.5 text-[var(--color-warning)]"
          :title="artifactUsageWarningTitle"
          aria-label="Artifact usage warning"
        >
          <ExclamationTriangleIcon class="w-3.5 h-3.5" />
        </div>
        <div
          v-if="showWorkspaceResourceWarning"
          class="flex items-center px-1.5 py-0.5 text-[var(--color-warning)]"
          :title="workspaceResourceWarningTitle"
          aria-label="Workspace cleanup recommendation"
        >
          <ExclamationTriangleIcon class="w-3.5 h-3.5" />
        </div>
      </template>
    </div>

    <!-- Right Section: Layout, Terminal & Version -->
    <div class="flex items-center gap-3 h-full">
      <div
        data-websocket-status
        class="flex items-center gap-1.5 h-full px-1 text-[10px] font-medium"
        :class="wsConnectionMeta.textClass"
        :title="`Realtime connection: ${wsConnectionMeta.label}`"
      >
        <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="wsConnectionMeta.dotClass"></span>
        <span>{{ wsConnectionMeta.label }}</span>
      </div>

      <div class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <!-- Workspace Layout Toggle -->
      <button
        @click="appStore.cycleWorkspaceLayoutMode()"
        class="flex items-center gap-1.5 h-full px-1.5 hover:bg-[var(--color-base)] transition-colors"
        :class="'text-[var(--color-accent)] font-medium'"
        :title="workspaceLayoutTitle"
        :aria-label="workspaceLayoutTitle"
        :aria-keyshortcuts="workspaceLayoutAriaShortcut"
      >
        <ViewColumnsIcon class="w-3.5 h-3.5" />
        <span>{{ workspaceLayoutLabel }}</span>
      </button>
      <span class="sr-only" aria-live="polite">{{ workspaceLayoutAnnouncement }}</span>

      <div class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <!-- Terminal Toggle -->
      <button
        @click="appStore.toggleTerminal()"
        class="flex items-center gap-1.5 h-full px-1.5 hover:bg-[var(--color-base)] transition-colors"
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
          class="relative flex items-center gap-1.5 h-full px-1.5 hover:bg-[var(--color-base)] transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]"
          title="Session notifications"
          @click="toggleNotificationsPanel"
        >
          <BellIcon class="w-3.5 h-3.5" />
          <span>Alerts</span>
          <span
            v-if="unreadNotificationCount > 0"
            class="absolute -right-0.5 -top-0.5 inline-flex min-w-[1rem] items-center justify-center rounded-full px-1 text-[9px] font-semibold leading-4 text-white"
            style="background-color: var(--color-error);"
          >
            {{ unreadNotificationBadge }}
          </span>
        </button>

        <div
          v-if="notificationsPanelOpen"
          class="layer-modal-dropdown absolute right-0 bottom-full mb-2 w-[24rem] overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-[var(--shadow-lifted)]"
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
      </div>

      <div class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <!-- Version -->
      <a
        href="https://inquiraai.com"
        @click.prevent="openInquiraSite"
        target="_blank"
        class="text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] transition-colors"
        style="font-family: var(--font-mono);"
        title="Visit inquiraai.com"
      >
        Inquira v{{ uiVersion }}
      </a>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import apiService from '../../services/apiService'
import { openExternalUrl } from '../../services/externalLinkService'
import { settingsWebSocket } from '../../services/websocketService'
import { formatUsageCompact, formatUsageTooltip } from '../../utils/usageFormat'
import {
  BellIcon,
  ChevronUpDownIcon,
  CommandLineIcon,
  ViewColumnsIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { toast, useToast } from '../../composables/useToast'

const appStore = useAppStore()
const authStore = useAuthStore()
const {
  notificationHistory,
  unreadNotificationCount,
  markAllNotificationsRead,
  clearNotificationHistory,
} = useToast()
const uiVersion = String(
  typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0'
).trim() || '0.0.0'

// --- Workspace Status Management ---
const workspaceRuntimeStatus = computed(() => appStore.activeWorkspaceRuntimeStatus)
const workspaceSwitcherOpen = ref(false)

const isWebSocketConnected = ref(false)
const isWebSocketMonitoringActive = ref(false)
let unsubscribeWebSocketConnection = null
let unsubscribeWorkspaceRuntimeStatus = null
let artifactUsageStreamAbortController = null
let artifactUsageReconnectTimer = null
let workspaceResourceRecommendationTimer = null
const lastWorkspaceResourceRecommendationKey = ref('')
const notificationsPanelOpen = ref(false)
const artifactUsage = ref({
  duckdbBytes: 0,
  duckdbWarningThresholdBytes: 1024 * 1024 * 1024,
  figureCount: 0,
  figureWarningThresholdCount: 20,
  duckdbWarning: false,
  figureWarning: false,
  warning: false,
})
const workspaceResourceRecommendation = ref(null)

const workspaceLayoutLabel = computed(() => {
  if (appStore.workspaceLayoutMode === 'chat') return 'Chat'
  if (appStore.workspaceLayoutMode === 'output') return 'Output'
  return 'View'
})

const workspaceLayoutTitle = computed(() => {
  return `${workspaceLayoutLabel.value} layout. Click to cycle View, Chat, and Output.`
})

const workspaceLayoutAriaShortcut = 'Control+Alt+V Meta+Alt+V Control+Alt+C Meta+Alt+C Control+Alt+O Meta+Alt+O'

const workspaceLayoutAnnouncement = computed(() => `${workspaceLayoutLabel.value} layout active`)

const unreadNotificationBadge = computed(() => {
  const count = Number(unreadNotificationCount.value || 0)
  if (count <= 0) return ''
  return count > 99 ? '99+' : String(count)
})

const tokenUsageSummaryLabel = computed(() => {
  const summary = appStore.activeConversationUsage && typeof appStore.activeConversationUsage === 'object'
    ? appStore.activeConversationUsage
    : null
  return formatUsageCompact(summary?.usage || appStore.liveTokenUsage)
})

const tokenUsageHoverLabel = computed(() => {
  const summary = appStore.activeConversationUsage && typeof appStore.activeConversationUsage === 'object'
    ? appStore.activeConversationUsage
    : null
  return formatUsageTooltip(summary?.usage || appStore.liveTokenUsage, summary)
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

const wsConnectionMeta = computed(() => {
  if (!isWebSocketMonitoringActive.value) {
    return {
      dotClass: 'bg-[var(--color-border-hover)]',
      textClass: 'text-[var(--color-text-muted)]',
      label: 'Inactive'
    }
  }
  if (isWebSocketConnected.value) {
    return {
      dotClass: 'bg-[var(--color-success)]',
      textClass: 'text-[var(--color-success)]',
      label: 'Connected'
    }
  }
  return {
    dotClass: 'bg-[var(--color-error)]',
    textClass: 'text-[var(--color-error)]',
    label: 'Disconnected'
  }
})

const activeWorkspaceName = computed(() => {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) return 'No workspace'
  const workspace = appStore.workspaces.find((item) => String(item?.id || '').trim() === workspaceId)
  return String(workspace?.name || '').trim() || 'Untitled workspace'
})

function runtimeStatusMeta(status) {
  switch (status) {
    case 'ready':
      return { dotClass: 'bg-[var(--color-success)]', textClass: 'text-[var(--color-success)]', label: 'Ready', showSpinner: false }
    case 'busy':
      return { dotClass: 'bg-[var(--color-warning)]', textClass: 'text-[var(--color-warning)]', label: 'Working', showSpinner: true }
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

function runtimeStatusMetaForWorkspace(workspaceId) {
  return runtimeStatusMeta(appStore.getWorkspaceRuntimeStatus(workspaceId))
}

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

const showArtifactUsageWarning = computed(() => {
  return Boolean(appStore.activeWorkspaceId && appStore.hasWorkspace && artifactUsage.value.warning)
})

const artifactUsageWarningTitle = computed(() => {
  const details = []
  if (artifactUsage.value.duckdbWarning) {
    details.push(
      `Turn artifacts: ${formatBytes(artifactUsage.value.duckdbBytes)} (limit ${formatBytes(artifactUsage.value.duckdbWarningThresholdBytes)})`
    )
  }
  if (artifactUsage.value.figureWarning) {
    details.push(
      `Charts saved: ${Number(artifactUsage.value.figureCount || 0)} (limit ${Number(artifactUsage.value.figureWarningThresholdCount || 20)})`
    )
  }
  if (!details.length) return 'Turn artifact usage is within safe limits.'
  return `Turn artifact usage warning. ${details.join(' | ')}. Delete unused artifacts to avoid performance issues.`
})

const workspaceResourceCandidates = computed(() => {
  const candidates = workspaceResourceRecommendation.value?.candidates
  return Array.isArray(candidates) ? candidates : []
})

const showWorkspaceResourceWarning = computed(() => {
  return workspaceResourceCandidates.value.length > 0
})

const workspaceResourceWarningTitle = computed(() => {
  const count = workspaceResourceCandidates.value.length
  if (count <= 0) return 'Workspace resource usage is within safe limits.'
  const names = workspaceResourceCandidates.value
    .map((candidate) => String(candidate?.workspace_name || candidate?.workspace_id || '').trim())
    .filter(Boolean)
    .slice(0, 3)
  const label = count === 1 ? 'workspace' : 'workspaces'
  return `Consider closing ${count} idle ${label}: ${names.join(', ')}`
})

function updateWebSocketStatus(connected) {
  const status = settingsWebSocket.getConnectionStatus()
  const shouldMonitor = Boolean(status.isPersistentMode || status.lastConnectionAttempt)
  isWebSocketMonitoringActive.value = shouldMonitor
  isWebSocketConnected.value = shouldMonitor ? connected : false
}

function setupWebSocketMonitoring() {
  if (typeof unsubscribeWebSocketConnection === 'function') {
    unsubscribeWebSocketConnection()
    unsubscribeWebSocketConnection = null
  }
  updateWebSocketStatus(settingsWebSocket.isConnected)
  unsubscribeWebSocketConnection = settingsWebSocket.onConnection((connected) => {
    updateWebSocketStatus(connected)
  })
  if (typeof unsubscribeWorkspaceRuntimeStatus === 'function') {
    unsubscribeWorkspaceRuntimeStatus()
    unsubscribeWorkspaceRuntimeStatus = null
  }
  unsubscribeWorkspaceRuntimeStatus = settingsWebSocket.subscribeWorkspaceRuntimeStatus(({ workspaceId, status }) => {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return
    appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, status)
    if (normalizedWorkspaceId !== String(appStore.activeWorkspaceId || '').trim()) return
    if (['ready', 'busy', 'starting'].includes(status)) {
      appStore.setRuntimeError('')
    }
  })
}

function resetArtifactUsage() {
  artifactUsage.value = {
    duckdbBytes: 0,
    duckdbWarningThresholdBytes: 1024 * 1024 * 1024,
    figureCount: 0,
    figureWarningThresholdCount: 20,
    duckdbWarning: false,
    figureWarning: false,
    warning: false,
  }
}

function formatBytes(bytes) {
  const value = Math.max(0, Number(bytes || 0))
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 ** 3) return `${(value / (1024 ** 2)).toFixed(1)} MB`
  return `${(value / (1024 ** 3)).toFixed(2)} GB`
}

function isUnauthorizedError(error) {
  const status = Number(error?.response?.status ?? error?.status ?? 0)
  if (status === 401) return true
  return String(error?.message || '').includes('401')
}

async function handleUnauthorizedPollingError() {
  stopArtifactUsageStream()
  settingsWebSocket.setWorkspaceRuntimeStatusWorkspace('')
  appStore.setWorkspaceRuntimeStatus(appStore.activeWorkspaceId, 'connecting')
  appStore.setRuntimeError('Background auth check failed. Reconnecting your session...')
  if (authStore.isAuthenticated) {
    await authStore.checkAuth({ preserveSession: true })
  }
  scheduleArtifactUsageReconnect()
}

function applyArtifactUsageSnapshot(payload) {
  artifactUsage.value = {
    duckdbBytes: Math.max(0, Number(payload?.duckdb_bytes || 0)),
    duckdbWarningThresholdBytes: Math.max(1, Number(payload?.duckdb_warning_threshold_bytes || 1024 * 1024 * 1024)),
    figureCount: Math.max(0, Number(payload?.figure_count || 0)),
    figureWarningThresholdCount: Math.max(1, Number(payload?.figure_warning_threshold_count || 20)),
    duckdbWarning: Boolean(payload?.duckdb_warning),
    figureWarning: Boolean(payload?.figure_warning),
    warning: Boolean(payload?.warning),
  }
}

async function startArtifactUsageStream() {
  if (!authStore.isAuthenticated) {
    resetArtifactUsage()
    return
  }
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId || !appStore.hasWorkspace) {
    resetArtifactUsage()
    return
  }
  stopArtifactUsageStream()
  artifactUsageStreamAbortController = new AbortController()
  const streamController = artifactUsageStreamAbortController
  try {
    await apiService.subscribeWorkspaceArtifactUsage(workspaceId, {
      signal: streamController.signal,
      onEvent: (event) => {
        if (event?.event !== 'snapshot') return
        applyArtifactUsageSnapshot(event.data)
      },
    })
    if (!streamController.signal.aborted) {
      scheduleArtifactUsageReconnect()
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    if (isUnauthorizedError(error)) {
      await handleUnauthorizedPollingError()
      return
    }
    resetArtifactUsage()
    scheduleArtifactUsageReconnect()
  }
}

function scheduleArtifactUsageReconnect(delayMs = 3000) {
  if (artifactUsageReconnectTimer) clearTimeout(artifactUsageReconnectTimer)
  artifactUsageReconnectTimer = setTimeout(() => {
    artifactUsageReconnectTimer = null
    if (!document.hidden) {
      void startArtifactUsageStream()
    }
  }, Math.max(0, Number(delayMs || 0)))
}

function stopArtifactUsageStream() {
  if (artifactUsageReconnectTimer) {
    clearTimeout(artifactUsageReconnectTimer)
    artifactUsageReconnectTimer = null
  }
  artifactUsageStreamAbortController?.abort()
  artifactUsageStreamAbortController = null
}

function workspaceResourceRecommendationKey(payload) {
  const candidates = Array.isArray(payload?.candidates) ? payload.candidates : []
  return candidates
    .map((candidate) => `${candidate?.workspace_id || ''}:${candidate?.idle_seconds || 0}`)
    .sort()
    .join('|')
}

async function refreshWorkspaceResourceRecommendation({ notify = false } = {}) {
  if (!authStore.isAuthenticated) {
    workspaceResourceRecommendation.value = null
    lastWorkspaceResourceRecommendationKey.value = ''
    return
  }
  try {
    const payload = await apiService.v1GetWorkspaceResourceRecommendation()
    workspaceResourceRecommendation.value = payload
    const candidates = Array.isArray(payload?.candidates) ? payload.candidates : []
    const key = workspaceResourceRecommendationKey(payload)
    if (notify && candidates.length > 0 && key && key !== lastWorkspaceResourceRecommendationKey.value) {
      toast.warning('Workspace cleanup suggested', workspaceResourceWarningTitle.value)
      lastWorkspaceResourceRecommendationKey.value = key
    }
    if (candidates.length === 0) {
      lastWorkspaceResourceRecommendationKey.value = ''
    }
  } catch (_error) {
    workspaceResourceRecommendation.value = null
  }
}

function startWorkspaceResourceRecommendationPolling() {
  stopWorkspaceResourceRecommendationPolling()
  void refreshWorkspaceResourceRecommendation({ notify: true })
  workspaceResourceRecommendationTimer = setInterval(() => {
    if (!document.hidden) {
      void refreshWorkspaceResourceRecommendation({ notify: true })
    }
  }, 60000)
}

function stopWorkspaceResourceRecommendationPolling() {
  if (workspaceResourceRecommendationTimer) {
    clearInterval(workspaceResourceRecommendationTimer)
    workspaceResourceRecommendationTimer = null
  }
}

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

function openInquiraSite() {
  void openExternalUrl('https://inquiraai.com')
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
  if (target.closest('[data-workspace-switcher]')) return
  closeWorkspaceSwitcher()
  closeNotificationsPanel()
}

function handleStatusBarEscape(event) {
  if (event.key === 'Escape') {
    closeWorkspaceSwitcher()
    closeNotificationsPanel()
  }
}

function syncWorkspaceRealtimeSubscriptions() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!authStore.isAuthenticated || !workspaceId || !appStore.hasWorkspace) {
    settingsWebSocket.setWorkspaceRuntimeStatusWorkspace('')
    stopArtifactUsageStream()
    appStore.setWorkspaceRuntimeStatus(workspaceId, 'missing')
    resetArtifactUsage()
    return
  }

  appStore.setWorkspaceRuntimeStatus(workspaceId, 'connecting')
  settingsWebSocket.setWorkspaceRuntimeStatusWorkspace(workspaceId)
  void refreshWorkspaceRuntimeStatusFromApi(workspaceId, 'connecting')
  void startArtifactUsageStream()
}

function toggleWorkspaceSwitcher() {
  workspaceSwitcherOpen.value = !workspaceSwitcherOpen.value
}

function closeWorkspaceSwitcher() {
  workspaceSwitcherOpen.value = false
}

async function selectWorkspaceFromStatusBar(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId || normalizedWorkspaceId === String(appStore.activeWorkspaceId || '').trim()) {
    closeWorkspaceSwitcher()
    return
  }
  try {
    await appStore.activateWorkspace(normalizedWorkspaceId)
    await appStore.fetchConversations()
  } catch (error) {
    toast.error('Workspace switch failed', error?.response?.data?.detail || error?.message || 'Could not switch workspace.')
  } finally {
    closeWorkspaceSwitcher()
  }
}

// Named handler so we can remove the exact same reference on unmount
function handleVisibilityChange() {
  if (!document.hidden && authStore.isAuthenticated && appStore.activeWorkspaceId && appStore.hasWorkspace) {
    syncWorkspaceRealtimeSubscriptions()
  }
}

// Lifecycle and Watchers
onMounted(() => {
  setupWebSocketMonitoring()
  syncWorkspaceRealtimeSubscriptions()
  startWorkspaceResourceRecommendationPolling()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  document.addEventListener('pointerdown', handleGlobalPointerDown)
  document.addEventListener('keydown', handleStatusBarEscape)
})

onUnmounted(() => {
  settingsWebSocket.setWorkspaceRuntimeStatusWorkspace('')
  stopArtifactUsageStream()
  stopWorkspaceResourceRecommendationPolling()
  resetArtifactUsage()
  if (typeof unsubscribeWorkspaceRuntimeStatus === 'function') {
    unsubscribeWorkspaceRuntimeStatus()
    unsubscribeWorkspaceRuntimeStatus = null
  }
  if (typeof unsubscribeWebSocketConnection === 'function') {
    unsubscribeWebSocketConnection()
    unsubscribeWebSocketConnection = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  document.removeEventListener('pointerdown', handleGlobalPointerDown)
  document.removeEventListener('keydown', handleStatusBarEscape)
})

watch([() => appStore.activeWorkspaceId, () => appStore.hasWorkspace, () => authStore.isAuthenticated], ([newId, hasWorkspace, isAuthenticated]) => {
  const normalizedWorkspaceId = String(newId || '').trim()
  if (isAuthenticated && newId && hasWorkspace) {
    syncWorkspaceRealtimeSubscriptions()
  } else {
    settingsWebSocket.setWorkspaceRuntimeStatusWorkspace('')
    stopArtifactUsageStream()
    workspaceResourceRecommendation.value = null
    appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, 'missing')
    resetArtifactUsage()
  }
})

watch(() => isWebSocketConnected.value, () => {
  syncWorkspaceRealtimeSubscriptions()
})

watch(() => authStore.isAuthenticated, (authenticated) => {
  if (authenticated) {
    startWorkspaceResourceRecommendationPolling()
  } else {
    stopWorkspaceResourceRecommendationPolling()
    workspaceResourceRecommendation.value = null
    lastWorkspaceResourceRecommendationKey.value = ''
  }
})
</script>
