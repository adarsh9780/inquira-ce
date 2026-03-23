<template>
  <div class="h-7 w-full bg-slate-50 border-t border-slate-200 flex items-center justify-between px-3 text-[11px] text-slate-600 select-none z-50 shrink-0">
    
    <!-- Left Section: Account, Editor Toggle, Kernel Status, and Editor Position -->
    <div class="flex items-center gap-2 h-full">
      <!-- Account Name (opens sidebar) -->
      <button
        v-if="authStore.isAuthenticated"
        @click.stop="openSidebar"
        class="max-w-[120px] truncate px-1 text-blue-600 text-left rounded hover:bg-slate-200/70 transition-colors"
        title="Open sidebar"
        aria-label="Open sidebar"
      >
        {{ accountDisplayLabel }}
      </button>

      <!-- Workspace/Schema Editor Toggle -->
      <div v-if="authStore.isAuthenticated" class="flex items-center gap-0.5 h-full">
        <button
          @click="switchToWorkspace"
          class="flex items-center gap-1 h-full px-1 rounded hover:bg-slate-200/50 transition-colors"
          :class="appStore.activeTab === 'workspace' ? 'text-blue-600 font-medium' : 'text-slate-500 hover:text-slate-700'"
          :title="'Switch to Workspace'"
        >
          <FolderOpenIcon class="w-3.5 h-3.5" />
        </button>
        <button
          @click="switchToSchemaEditor"
          class="flex items-center gap-1 h-full px-1 rounded hover:bg-slate-200/50 transition-colors"
          :class="appStore.activeTab === 'schema-editor' ? 'text-blue-600 font-medium' : 'text-slate-500 hover:text-slate-700'"
          :title="'Switch to Schema Editor'"
        >
          <DocumentTextIcon class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Sidebar Toggle -->
      <button
        v-if="authStore.isAuthenticated"
        @click.stop="toggleSidebarFromStatusBar"
        class="h-5 w-5 rounded hover:bg-slate-200/70 flex items-center justify-center transition-colors"
        :class="appStore.isSidebarCollapsed ? 'text-slate-500 hover:text-slate-700' : 'text-blue-600'"
        :title="sidebarToggleTitle"
        aria-label="Toggle sidebar"
      >
        <ChevronRightIcon v-if="appStore.isSidebarCollapsed" class="w-3.5 h-3.5" />
        <ChevronLeftIcon v-else class="w-3.5 h-3.5" />
      </button>

      <div v-if="authStore.isAuthenticated" class="w-px h-3.5 bg-slate-300"></div>

      <!-- Kernel Status -->
      <div class="flex items-center gap-1.5 h-full px-1">
        <span
          v-if="kernelStatusMeta.showSpinner"
          class="inline-block w-2 h-2 rounded-full border-[1.5px] border-blue-200 border-t-blue-600 animate-spin shrink-0"
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
            class="p-0.5 rounded hover:bg-slate-200 hover:text-amber-600 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            title="Interrupt Kernel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path d="M5.25 3A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17h9.5A2.25 2.25 0 0017 14.75v-9.5A2.25 2.25 0 0014.75 3h-9.5zM6 6.75a.75.75 0 01.75-.75h6.5a.75.75 0 01.75.75v6.5a.75.75 0 01-.75.75h-6.5a.75.75 0 01-.75-.75v-6.5z" /></svg>
          </button>
          <button
            @click="restartKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning"
            class="p-0.5 rounded hover:bg-slate-200 hover:text-red-500 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            title="Restart Kernel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" /></svg>
          </button>
        </div>
      </div>

      <template v-if="appStore.isEditorFocused">
        <div class="w-px h-3.5 bg-slate-300"></div>
        <div class="flex items-center text-slate-500 font-mono tracking-tight gap-1 px-1">
          <span>Ln {{ appStore.editorLine }},</span>
          <span>Col {{ appStore.editorCol }}</span>
        </div>
      </template>
    </div>

    <!-- Center Section: Data pane status -->
    <div class="flex items-center gap-2 h-full">
      <!-- Data pane error takes priority -->
      <template v-if="appStore.dataPaneError">
        <div class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-red-50 text-red-600 max-w-[280px] truncate"
             :title="appStore.dataPaneError">
          <span class="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0"></span>
          <span class="truncate">{{ appStore.dataPaneError }}</span>
        </div>
      </template>
      <template v-else>
        <div v-if="appStore.activeWorkspaceId && paneArtifactCountLabel" class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium"
             :class="artifactCountClass">
          <span>{{ paneArtifactCountLabel }}</span>
        </div>
        <div v-if="appStore.activeWorkspaceId && tableViewportLabel" class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700">
          <span>{{ tableViewportLabel }}</span>
        </div>
        <div
          v-if="showArtifactUsageWarning"
          class="flex items-center px-1.5 py-0.5 text-amber-600"
          :title="artifactUsageWarningTitle"
          aria-label="Artifact usage warning"
        >
          <ExclamationTriangleIcon class="w-3.5 h-3.5" />
        </div>
      </template>
    </div>

    <!-- Right Section: Data Focus, Terminal & Version -->
    <div class="flex items-center gap-2 h-full">
      <!-- Data Focus Toggle -->
      <button
        @click="appStore.toggleDataFocusMode()"
        class="flex items-center gap-1.5 h-full px-1.5 hover:bg-slate-200/50 hover:text-slate-900 transition-colors"
        :class="appStore.isDataFocusMode ? 'text-blue-600 font-medium' : ''"
        :title="dataFocusToggleTitle"
      >
        <ViewColumnsIcon class="w-3.5 h-3.5" />
        <span>Data Focus</span>
      </button>

      <div class="w-px h-3.5 bg-slate-300"></div>

      <!-- Terminal Toggle -->
      <button 
        @click="appStore.toggleTerminal()"
        class="flex items-center gap-1.5 h-full px-1.5 hover:bg-slate-200/50 hover:text-slate-900 transition-colors"
        :class="appStore.isTerminalOpen ? 'text-blue-600 font-medium' : ''"
        title="Toggle terminal panel (Cmd/Ctrl+J)"
      >
        <CommandLineIcon class="w-3.5 h-3.5" />
        <span>Terminal</span>
      </button>

      <div class="w-px h-3.5 bg-slate-300"></div>

      <!-- Version -->
      <a 
        href="https://github.com/adarsh9780/inquira" 
        @click.prevent="openGitHubRepo"
        target="_blank" 
        class="text-slate-400 hover:text-slate-600 transition-colors font-mono"
        title="View on GitHub"
      >
        Inquira v0.5.7
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

// --- Kernel Status Management ---
const kernelStatus = ref('missing')
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
      dotClass: 'bg-slate-300',
      textClass: 'text-slate-500',
      label: 'Inactive'
    }
  }
  if (isWebSocketConnected.value) {
    return {
      dotClass: 'bg-green-500',
      textClass: 'text-green-700',
      label: 'Connected'
    }
  }
  return {
    dotClass: 'bg-red-500',
    textClass: 'text-red-600',
    label: 'Disconnected'
  }
})

const kernelStatusMeta = computed(() => {
  switch (kernelStatus.value) {
    case 'ready':
      return { dotClass: 'bg-green-500', textClass: 'text-green-700', label: 'Kernel Ready', showSpinner: false }
    case 'busy':
      return { dotClass: 'bg-amber-500', textClass: 'text-amber-700', label: 'Kernel Busy', showSpinner: true }
    case 'starting':
    case 'connecting':
      return { dotClass: 'bg-blue-400', textClass: 'text-blue-600', label: 'Kernel Starting', showSpinner: true }
    case 'error':
      return { dotClass: 'bg-red-500', textClass: 'text-red-700', label: 'Kernel Error', showSpinner: false }
    case 'missing':
    default:
      return { dotClass: 'bg-gray-400', textClass: 'text-gray-500', label: 'No Kernel', showSpinner: false }
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
  // Subtle muted pill — informational, not actionable
  return 'bg-slate-100 text-slate-500'
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

function openSidebar() {
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
    if (workspaceId !== String(appStore.activeWorkspaceId || '').trim()) return
    kernelStatus.value = status
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
  kernelStatus.value = 'connecting'
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

function openGitHubRepo() {
  void openExternalUrl('https://github.com/adarsh9780/inquira')
}

function syncWorkspaceRealtimeSubscriptions() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!authStore.isAuthenticated || !workspaceId || !appStore.hasWorkspace) {
    settingsWebSocket.setKernelStatusWorkspace('')
    stopArtifactUsageStream()
    kernelStatus.value = 'missing'
    resetArtifactUsage()
    return
  }

  kernelStatus.value = 'connecting'
  settingsWebSocket.setKernelStatusWorkspace(workspaceId)
  void startArtifactUsageStream()
}

async function interruptKernel() {
  if (!appStore.activeWorkspaceId || !appStore.hasWorkspace || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  try {
    const response = await apiService.v1InterruptWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) toast.success('Kernel Interrupted', 'Execution interrupt signal sent.')
    else toast.error('Interrupt Failed', 'No running kernel found.')
  } catch (error) {
    toast.error('Interrupt Failed', error?.response?.data?.detail || error.message)
  } finally {
    isKernelActionRunning.value = false
  }
}

async function restartKernel() {
  if (!appStore.activeWorkspaceId || !appStore.hasWorkspace || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  kernelStatus.value = 'connecting'
  try {
    const response = await apiService.v1RestartWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) {
      appStore.setCodeRunning(false)
      toast.success('Kernel Restarted', 'Workspace kernel has been restarted.')
    } else {
      toast.error('Restart Failed', 'No kernel session existed.')
    }
  } catch (error) {
    toast.error('Restart Failed', error?.response?.data?.detail || error.message)
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
  if (isAuthenticated && newId && hasWorkspace) {
    syncWorkspaceRealtimeSubscriptions()
  } else {
    settingsWebSocket.setKernelStatusWorkspace('')
    stopArtifactUsageStream()
    kernelStatus.value = 'missing'
    resetArtifactUsage()
  }
})

watch(() => isWebSocketConnected.value, () => {
  syncWorkspaceRealtimeSubscriptions()
})
</script>
