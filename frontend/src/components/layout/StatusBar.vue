<template>
  <div class="h-7 w-full bg-[var(--color-surface)] border-t border-[var(--color-border)] flex items-center justify-between px-3 text-[12px] text-[var(--color-text-muted)] select-none z-50 shrink-0">

    <!-- Left Section: Account, Editor Toggle, Kernel Status, and Editor Position -->
    <div class="flex items-center gap-3 h-full">
      <!-- Account Name with Sidebar Toggle (chevron beside username) -->
      <button
        v-if="authStore.isAuthenticated"
        @click.stop="toggleSidebarFromStatusBar"
        class="flex items-center gap-1 max-w-[150px] truncate px-1 text-[var(--color-accent)] text-left rounded hover:bg-[var(--color-base)] transition-colors"
        :title="sidebarToggleTitle"
        :aria-label="sidebarToggleTitle"
      >
        <span class="truncate">{{ accountDisplayLabel }}</span>
        <ChevronLeftIcon v-if="!appStore.isSidebarCollapsed" class="w-3.5 h-3.5 shrink-0" />
        <ChevronRightIcon v-else class="w-3.5 h-3.5 shrink-0" />
      </button>

      <div class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <!-- Workspace/Schema Editor Toggle -->
      <div v-if="authStore.isAuthenticated" class="flex items-center gap-0.5 h-full">
        <button
          @click="switchToWorkspace"
          class="flex items-center gap-1 h-full px-1 rounded hover:bg-[var(--color-base)] transition-colors"
          :class="appStore.activeTab === 'workspace' ? 'text-[var(--color-accent)] font-medium' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
          :title="'Switch to Workspace'"
        >
          <FolderOpenIcon class="w-3.5 h-3.5" />
        </button>
        <button
          @click="switchToSchemaEditor"
          class="flex items-center gap-1 h-full px-1 rounded hover:bg-[var(--color-base)] transition-colors"
          :class="appStore.activeTab === 'schema-editor' ? 'text-[var(--color-accent)] font-medium' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
          :title="'Switch to Schema Editor'"
        >
          <DocumentTextIcon class="w-3.5 h-3.5" />
        </button>
      </div>

      <div v-if="authStore.isAuthenticated" class="w-px h-3.5 bg-[var(--color-border)]"></div>

      <!-- Kernel Status -->
      <div class="flex items-center gap-1.5 h-full px-1">
        <span
          v-if="kernelStatusMeta.showSpinner"
          class="inline-block w-2 h-2 rounded-full border-[1.5px] border-[var(--color-border)] border-t-[var(--color-text-main)] animate-spin shrink-0"
          aria-hidden="true"
        ></span>
        <span v-else class="w-2 h-2 rounded-full shrink-0" :class="kernelStatusMeta.dotClass"></span>
        <span class="font-medium mr-2" :class="kernelStatusMeta.textClass">
          {{ kernelStatusMeta.label }}
        </span>

        <!-- Kernel Actions -->
        <div class="flex items-center gap-0.5 ml-1">
          <button
            @click="interruptKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning || kernelStatus === 'missing'"
            class="p-0.5 rounded hover:bg-[var(--color-warning)]/10 text-[var(--color-text-muted)] hover:text-[var(--color-warning)] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            title="Interrupt Kernel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path d="M5.25 3A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17h9.5A2.25 2.25 0 0017 14.75v-9.5A2.25 2.25 0 0014.75 3h-9.5zM6 6.75a.75.75 0 01.75-.75h6.5a.75.75 0 01.75.75v6.5a.75.75 0 01-.75.75h-6.5a.75.75 0 01-.75-.75v-6.5z" /></svg>
          </button>
          <button
            @click="restartKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning"
            class="p-0.5 rounded hover:bg-[var(--color-error)]/10 text-[var(--color-text-muted)] hover:text-[var(--color-error)] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            title="Restart Kernel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" /></svg>
          </button>
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
      </template>
    </div>

    <!-- Right Section: Data Focus, Terminal & Version -->
    <div class="flex items-center gap-3 h-full">
      <!-- Data Focus Toggle -->
      <button
        @click="appStore.toggleDataFocusMode()"
        class="flex items-center gap-1.5 h-full px-1.5 hover:bg-[var(--color-base)] transition-colors"
        :class="appStore.isDataFocusMode ? 'text-[var(--color-accent)] font-medium' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
        :title="dataFocusToggleTitle"
      >
        <ViewColumnsIcon class="w-3.5 h-3.5" />
        <span>Data Focus</span>
      </button>

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
import {
  CommandLineIcon,
  ViewColumnsIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  ExclamationTriangleIcon,
  FolderOpenIcon,
  DocumentTextIcon,
} from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'

const appStore = useAppStore()
const authStore = useAuthStore()
const uiVersion = String(
  typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0'
).trim() || '0.0.0'

// --- Kernel Status Management ---
const kernelStatus = computed(() => appStore.activeWorkspaceKernelStatus)
const isKernelActionRunning = ref(false)

const isWebSocketConnected = ref(false)
const isWebSocketMonitoringActive = ref(false)
let unsubscribeWebSocketConnection = null
let unsubscribeKernelStatus = null
let artifactUsageStreamAbortController = null
let artifactUsageReconnectTimer = null
const artifactUsage = ref({
  duckdbBytes: 0,
  duckdbWarningThresholdBytes: 1024 * 1024 * 1024,
  figureCount: 0,
  figureWarningThresholdCount: 20,
  duckdbWarning: false,
  figureWarning: false,
  warning: false,
})

const accountLabel = computed(() => {
  const username = String(authStore.username || '').trim()
  return username || 'Account'
})

const accountDisplayLabel = computed(() => {
  const value = String(accountLabel.value || '').trim()
  if (!value) return 'Account'
  if (value.includes('@')) return value
  if (!value.includes(' ')) {
    return value.charAt(0).toUpperCase() + value.slice(1)
  }
  return value
    .split(/\s+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ')
})

const sidebarToggleTitle = computed(() => {
  if (appStore.isSidebarCollapsed) return 'Show sidebar (Cmd/Ctrl+B)'
  return 'Hide sidebar (Cmd/Ctrl+B)'
})

const dataFocusToggleTitle = computed(() => {
  if (appStore.isDataFocusMode) return 'Exit data focus mode (Cmd/Ctrl+Shift+D)'
  return 'Enter data focus mode (Cmd/Ctrl+Shift+D)'
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

const kernelStatusMeta = computed(() => {
  switch (kernelStatus.value) {
    case 'ready':
      return { dotClass: 'bg-[var(--color-success)]', textClass: 'text-[var(--color-success)]', label: 'Kernel Ready', showSpinner: false }
    case 'busy':
      return { dotClass: 'bg-[var(--color-warning)]', textClass: 'text-[var(--color-warning)]', label: 'Kernel Busy', showSpinner: true }
    case 'starting':
    case 'connecting':
      return { dotClass: 'bg-[var(--color-accent)]', textClass: 'text-[var(--color-accent)]', label: 'Kernel Starting', showSpinner: true }
    case 'error':
      return { dotClass: 'bg-[var(--color-error)]', textClass: 'text-[var(--color-error)]', label: 'Kernel Error', showSpinner: false }
    case 'missing':
    default:
      return { dotClass: 'bg-[var(--color-text-muted)]', textClass: 'text-[var(--color-text-muted)]', label: 'No Kernel', showSpinner: false }
  }
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

const showArtifactUsageWarning = computed(() => {
  return Boolean(appStore.activeWorkspaceId && appStore.hasWorkspace && artifactUsage.value.warning)
})

const artifactUsageWarningTitle = computed(() => {
  const details = []
  if (artifactUsage.value.duckdbWarning) {
    details.push(
      `DuckDB artifacts: ${formatBytes(artifactUsage.value.duckdbBytes)} (limit ${formatBytes(artifactUsage.value.duckdbWarningThresholdBytes)})`
    )
  }
  if (artifactUsage.value.figureWarning) {
    details.push(
      `Charts saved: ${Number(artifactUsage.value.figureCount || 0)} (limit ${Number(artifactUsage.value.figureWarningThresholdCount || 20)})`
    )
  }
  if (!details.length) return 'Scratchpad artifact usage is within safe limits.'
  return `Scratchpad usage warning. ${details.join(' | ')}. Delete unused artifacts to avoid performance issues.`
})

function toggleSidebarFromStatusBar() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function switchToWorkspace() {
  appStore.setActiveTab('workspace')
}

function switchToSchemaEditor() {
  appStore.setActiveTab('schema-editor')
}

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
  if (typeof unsubscribeKernelStatus === 'function') {
    unsubscribeKernelStatus()
    unsubscribeKernelStatus = null
  }
  unsubscribeKernelStatus = settingsWebSocket.subscribeKernelStatus(({ workspaceId, status }) => {
    const normalizedWorkspaceId = String(workspaceId || '').trim()
    if (!normalizedWorkspaceId) return
    appStore.setWorkspaceKernelStatus(normalizedWorkspaceId, status)
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
  settingsWebSocket.setKernelStatusWorkspace('')
  appStore.setWorkspaceKernelStatus(appStore.activeWorkspaceId, 'connecting')
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

async function refreshKernelStatusFromApi(workspaceId, fallbackStatus = 'missing') {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return 'missing'
  try {
    const payload = await apiService.v1GetWorkspaceKernelStatus(normalizedWorkspaceId)
    const status = String(payload?.status || '').trim().toLowerCase() || fallbackStatus
    appStore.setWorkspaceKernelStatus(normalizedWorkspaceId, status)
    return status
  } catch (_error) {
    appStore.setWorkspaceKernelStatus(normalizedWorkspaceId, fallbackStatus)
    return fallbackStatus
  }
}

function openInquiraSite() {
  void openExternalUrl('https://inquiraai.com')
}

function syncWorkspaceRealtimeSubscriptions() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!authStore.isAuthenticated || !workspaceId || !appStore.hasWorkspace) {
    settingsWebSocket.setKernelStatusWorkspace('')
    stopArtifactUsageStream()
    appStore.setWorkspaceKernelStatus(workspaceId, 'missing')
    resetArtifactUsage()
    return
  }

  appStore.setWorkspaceKernelStatus(workspaceId, 'connecting')
  settingsWebSocket.setKernelStatusWorkspace(workspaceId)
  void refreshKernelStatusFromApi(workspaceId, 'connecting')
  void startArtifactUsageStream()
}

async function interruptKernel() {
  if (!appStore.activeWorkspaceId || !appStore.hasWorkspace || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  appStore.setWorkspaceKernelStatus(workspaceId, 'busy')
  try {
    const response = await apiService.v1InterruptWorkspaceKernel(workspaceId)
    if (response?.reset) toast.success('Kernel Interrupted', 'Execution interrupt signal sent.')
    else toast.error('Interrupt Failed', 'No running kernel found.')
    await refreshKernelStatusFromApi(workspaceId, response?.reset ? 'ready' : 'missing')
  } catch (error) {
    toast.error('Interrupt Failed', error?.response?.data?.detail || error.message)
    await refreshKernelStatusFromApi(workspaceId, 'error')
  } finally {
    isKernelActionRunning.value = false
  }
}

async function restartKernel() {
  if (!appStore.activeWorkspaceId || !appStore.hasWorkspace || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  appStore.setWorkspaceKernelStatus(workspaceId, 'connecting')
  try {
    const response = await apiService.v1RestartWorkspaceKernel(workspaceId)
    if (response?.reset) {
      appStore.setCodeRunning(false)
      toast.success('Kernel Restarted', 'Workspace kernel has been restarted.')
    } else {
      toast.error('Restart Failed', 'No kernel session existed.')
    }
    await refreshKernelStatusFromApi(workspaceId, response?.reset ? 'starting' : 'missing')
  } catch (error) {
    toast.error('Restart Failed', error?.response?.data?.detail || error.message)
    await refreshKernelStatusFromApi(workspaceId, 'error')
  } finally {
    isKernelActionRunning.value = false
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
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  settingsWebSocket.setKernelStatusWorkspace('')
  stopArtifactUsageStream()
  resetArtifactUsage()
  if (typeof unsubscribeKernelStatus === 'function') {
    unsubscribeKernelStatus()
    unsubscribeKernelStatus = null
  }
  if (typeof unsubscribeWebSocketConnection === 'function') {
    unsubscribeWebSocketConnection()
    unsubscribeWebSocketConnection = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

watch([() => appStore.activeWorkspaceId, () => appStore.hasWorkspace, () => authStore.isAuthenticated], ([newId, hasWorkspace, isAuthenticated]) => {
  const normalizedWorkspaceId = String(newId || '').trim()
  if (isAuthenticated && newId && hasWorkspace) {
    syncWorkspaceRealtimeSubscriptions()
  } else {
    settingsWebSocket.setKernelStatusWorkspace('')
    stopArtifactUsageStream()
    appStore.setWorkspaceKernelStatus(normalizedWorkspaceId, 'missing')
    resetArtifactUsage()
  }
})

watch(() => isWebSocketConnected.value, () => {
  syncWorkspaceRealtimeSubscriptions()
})
</script>
