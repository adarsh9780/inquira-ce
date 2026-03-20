<template>
  <div class="h-7 w-full bg-slate-50 border-t border-slate-200 flex items-center justify-between px-3 text-[11px] text-slate-600 select-none z-50 shrink-0">
    
    <!-- Left Section: Account, Kernel Status, and Editor Position -->
    <div class="flex items-center gap-2 h-full">
      <div ref="accountMenuRef" class="relative" v-if="authStore.isAuthenticated">
        <div class="flex items-center h-full gap-0.5">
          <button
            @click.stop="toggleAccountMenu"
            class="max-w-[120px] truncate px-1 text-blue-600 text-left rounded hover:bg-slate-200/70 transition-colors"
            :title="accountMenuTitle"
            aria-label="Toggle account menu"
          >
            {{ accountDisplayLabel }}
          </button>
          <button
            @click.stop="toggleAccountMenu"
            class="h-5 w-5 rounded hover:bg-slate-200/70 flex items-center justify-center transition-colors"
            :class="isAccountMenuOpen ? 'text-blue-600' : 'text-slate-500 hover:text-slate-700'"
            :title="accountMenuTitle"
            aria-label="Toggle account menu"
          >
            <ChevronDownIcon v-if="isAccountMenuOpen" class="w-3.5 h-3.5" />
            <ChevronUpIcon v-else class="w-3.5 h-3.5" />
          </button>
          <button
            @click.stop="toggleSidebarFromStatusBar"
            class="h-5 w-5 rounded hover:bg-slate-200/70 flex items-center justify-center transition-colors"
            :class="appStore.isSidebarCollapsed ? 'text-slate-500 hover:text-slate-700' : 'text-blue-600'"
            :title="sidebarToggleTitle"
            aria-label="Toggle sidebar"
          >
            <ChevronRightIcon v-if="appStore.isSidebarCollapsed" class="w-3.5 h-3.5" />
            <ChevronLeftIcon v-else class="w-3.5 h-3.5" />
          </button>
        </div>

        <div
          v-if="isAccountMenuOpen"
          class="absolute bottom-full left-0 mb-1 w-56 rounded-lg shadow-lg z-50 overflow-hidden text-left"
          style="background-color: var(--color-surface); border: 1px solid var(--color-border);"
        >
          <div class="px-3 py-2 border-b" style="border-color: var(--color-border); background-color: var(--color-base);">
            <p class="text-[11px] font-semibold truncate" style="color: var(--color-text-main);">{{ accountDisplayLabel }}</p>
            <p class="text-[10px] truncate" style="color: var(--color-text-muted);">{{ authStore.planLabel }}</p>
          </div>
          <div class="px-3 py-2 border-b text-[10px] space-y-1.5" style="border-color: var(--color-border);">
            <div class="flex items-center justify-between gap-3">
              <span style="color: var(--color-text-muted);">WS Connection</span>
              <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full shrink-0" :class="wsConnectionMeta.dotClass"></span>
                <span class="font-medium" :class="wsConnectionMeta.textClass">{{ wsConnectionMeta.label }}</span>
              </div>
            </div>
            <div class="flex items-center justify-between gap-3">
              <span style="color: var(--color-text-muted);">Kernel Status</span>
              <div class="flex items-center gap-1.5">
                <span
                  v-if="kernelStatusMeta.showSpinner"
                  class="inline-block w-2 h-2 rounded-full border-[1.5px] border-blue-200 border-t-blue-600 animate-spin shrink-0"
                  aria-hidden="true"
                ></span>
                <span v-else class="w-2 h-2 rounded-full shrink-0" :class="kernelStatusMeta.dotClass"></span>
                <span class="font-medium" :class="kernelStatusMeta.textClass">{{ kernelStatusMeta.label }}</span>
              </div>
            </div>
          </div>
          <div class="py-1">
            <button
              @click="openSettings('api')"
              class="w-full text-left px-3 py-1.5 text-[11px] font-medium hover:bg-zinc-50 transition-colors"
              style="color: var(--color-text-main);"
            >
              Settings
            </button>
            <button
              @click="openTerms"
              class="w-full text-left px-3 py-1.5 text-[11px] font-medium hover:bg-zinc-50 transition-colors"
              style="color: var(--color-text-main);"
            >
              Terms &amp; Conditions
            </button>
            <div class="border-t my-1" style="border-color: var(--color-border);"></div>
            <button
              @click="promptLogout"
              class="w-full text-left px-3 py-1.5 text-[11px] font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

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

    <!-- Right Section: Terminal & Version -->
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

    <SettingsModal
      :is-open="isSettingsOpen"
      :initial-tab="settingsInitialTab"
      @close="closeSettings"
    />
    <ConfirmationModal
      :is-open="isLogoutConfirmOpen"
      title="Confirm Logout"
      :message="`Are you sure you want to log out, ${accountDisplayLabel}?`"
      confirm-text="Log Out"
      cancel-text="Cancel"
      @close="cancelLogout"
      @confirm="confirmLogout"
    />
    <div
      v-if="isTermsDialogOpen"
      class="fixed inset-0 z-[70] flex items-center justify-center px-4"
      @click="closeTermsDialog"
    >
      <div class="absolute inset-0 bg-black/10 backdrop-blur-[1.5px]"></div>
      <div
        class="relative w-full max-w-3xl rounded-xl border shadow-2xl"
        style="background-color: var(--color-surface); border-color: var(--color-border); color: var(--color-text-main);"
        @click.stop
      >
        <div class="flex items-center justify-between border-b px-5 py-3" style="border-color: var(--color-border);">
          <div>
            <p class="text-sm font-semibold">Terms &amp; Conditions</p>
            <p v-if="termsLastUpdated" class="text-xs" style="color: var(--color-text-muted);">Last updated: {{ termsLastUpdated }}</p>
          </div>
          <button
            class="btn-icon h-7 w-7 p-1.5 border"
            style="border-color: var(--color-border); color: var(--color-text-main); background-color: var(--color-base);"
            title="Close terms"
            aria-label="Close terms"
            @click="closeTermsDialog"
          >
            <XMarkIcon class="h-4 w-4" />
          </button>
        </div>
        <div class="max-h-[70vh] overflow-y-auto px-5 py-4 text-sm leading-6">
          <p v-if="isTermsLoading" style="color: var(--color-text-muted);">Loading terms...</p>
          <p v-else-if="termsError" class="rounded-md border px-3 py-2 text-xs text-red-700 bg-red-50" style="border-color: #fca5a5;">
            {{ termsError }}
          </p>
          <div
            v-else
            class="terms-markdown-content"
            v-html="termsHtml"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import apiService from '../../services/apiService'
import { openExternalUrl } from '../../services/externalLinkService'
import { settingsWebSocket } from '../../services/websocketService'
import {
  CommandLineIcon,
  ViewColumnsIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'
import SettingsModal from '../modals/SettingsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'

const appStore = useAppStore()
const authStore = useAuthStore()

// --- Kernel Status Management ---
const kernelStatus = ref('missing')
const isKernelStatusRequestInFlight = ref(false)
const isKernelActionRunning = ref(false)
let kernelStatusPoller = null
let artifactUsagePoller = null
let artifactUsageRefreshTimer = null
let artifactUsageAbortController = null

const accountMenuRef = ref(null)
const isAccountMenuOpen = ref(false)
const isTermsDialogOpen = ref(false)
const isTermsLoading = ref(false)
const termsError = ref('')
const termsMarkdown = ref('')
const termsLastUpdated = ref('')
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api')
const isLogoutConfirmOpen = ref(false)
const isWebSocketConnected = ref(false)
const isWebSocketMonitoringActive = ref(false)
let unsubscribeWebSocketConnection = null
const isArtifactUsageRequestInFlight = ref(false)
const artifactUsage = ref({
  duckdbBytes: 0,
  duckdbWarningThresholdBytes: 1024 * 1024 * 1024,
  figureCount: 0,
  figureWarningThresholdCount: 20,
  duckdbWarning: false,
  figureWarning: false,
  warning: false,
})
const termsMarkdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})
const termsHtml = computed(() => {
  const raw = String(termsMarkdown.value || '').trim()
  if (!raw) return ''
  return DOMPurify.sanitize(termsMarkdownRenderer.render(raw), {
    USE_PROFILES: { html: true },
  })
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

const accountMenuTitle = computed(() => {
  return isAccountMenuOpen.value ? 'Close account menu' : 'Open account menu'
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

function toggleAccountMenu() {
  isAccountMenuOpen.value = !isAccountMenuOpen.value
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
  stopKernelStatusPolling()
  stopArtifactUsagePolling()
  kernelStatus.value = 'missing'
  resetArtifactUsage()
  appStore.setRuntimeError('Session expired. Please sign in again.')
  if (authStore.isAuthenticated) {
    await authStore.checkAuth()
  }
}

async function refreshArtifactUsage() {
  if (!authStore.isAuthenticated) {
    resetArtifactUsage()
    return
  }
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId || !appStore.hasWorkspace) {
    resetArtifactUsage()
    return
  }
  if (isArtifactUsageRequestInFlight.value) return

  isArtifactUsageRequestInFlight.value = true
  artifactUsageAbortController?.abort()
  artifactUsageAbortController = new AbortController()
  try {
    const payload = await apiService.v1GetWorkspaceArtifactUsage(workspaceId, {
      signal: artifactUsageAbortController.signal,
    })
    artifactUsage.value = {
      duckdbBytes: Math.max(0, Number(payload?.duckdb_bytes || 0)),
      duckdbWarningThresholdBytes: Math.max(1, Number(payload?.duckdb_warning_threshold_bytes || 1024 * 1024 * 1024)),
      figureCount: Math.max(0, Number(payload?.figure_count || 0)),
      figureWarningThresholdCount: Math.max(1, Number(payload?.figure_warning_threshold_count || 20)),
      duckdbWarning: Boolean(payload?.duckdb_warning),
      figureWarning: Boolean(payload?.figure_warning),
      warning: Boolean(payload?.warning),
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    if (isUnauthorizedError(error)) {
      await handleUnauthorizedPollingError()
      return
    }
    resetArtifactUsage()
  } finally {
    isArtifactUsageRequestInFlight.value = false
  }
}

function scheduleArtifactUsageRefresh(delayMs = 250) {
  if (artifactUsageRefreshTimer) clearTimeout(artifactUsageRefreshTimer)
  artifactUsageRefreshTimer = setTimeout(() => {
    artifactUsageRefreshTimer = null
    void refreshArtifactUsage()
  }, Math.max(0, Number(delayMs || 0)))
}

function startArtifactUsagePolling() {
  if (!authStore.isAuthenticated) return
  stopArtifactUsagePolling()
  void refreshArtifactUsage()
  artifactUsagePoller = setInterval(() => {
    if (!document.hidden && authStore.isAuthenticated) void refreshArtifactUsage()
  }, 15000)
}

function stopArtifactUsagePolling() {
  if (artifactUsagePoller) {
    clearInterval(artifactUsagePoller)
    artifactUsagePoller = null
  }
  if (artifactUsageRefreshTimer) {
    clearTimeout(artifactUsageRefreshTimer)
    artifactUsageRefreshTimer = null
  }
  artifactUsageAbortController?.abort()
  artifactUsageAbortController = null
  isArtifactUsageRequestInFlight.value = false
}

function openSettings(tab = 'api') {
  settingsInitialTab.value = tab
  isSettingsOpen.value = true
  isAccountMenuOpen.value = false
}

function closeSettings() {
  isSettingsOpen.value = false
  settingsInitialTab.value = 'api'
}

function openGitHubRepo() {
  void openExternalUrl('https://github.com/adarsh9780/inquira')
}

async function loadTermsAndConditions({ force = false } = {}) {
  if (termsMarkdown.value && !force) return
  isTermsLoading.value = true
  termsError.value = ''
  try {
    const payload = await apiService.v1GetTermsAndConditions()
    termsMarkdown.value = String(payload?.markdown || '').trim()
    termsLastUpdated.value = String(payload?.last_updated || '').trim()
  } catch (error) {
    termsError.value = error?.message || 'Failed to load Terms & Conditions.'
  } finally {
    isTermsLoading.value = false
  }
}

async function openTerms() {
  isAccountMenuOpen.value = false
  isTermsDialogOpen.value = true
  await loadTermsAndConditions()
}

function closeTermsDialog() {
  isTermsDialogOpen.value = false
}

function promptLogout() {
  isLogoutConfirmOpen.value = true
  isAccountMenuOpen.value = false
}

function cancelLogout() {
  isLogoutConfirmOpen.value = false
}

async function confirmLogout() {
  isLogoutConfirmOpen.value = false
  try {
    await authStore.logout()
  } catch (error) {
    toast.error('Logout Failed', error?.message || 'Failed to logout.')
  }
}

async function refreshKernelStatus() {
  if (!authStore.isAuthenticated) {
    kernelStatus.value = 'missing'
    return
  }
  if (!appStore.activeWorkspaceId || !appStore.hasWorkspace) {
    kernelStatus.value = 'missing'
    return
  }
  if (isKernelStatusRequestInFlight.value) return
  isKernelStatusRequestInFlight.value = true
  try {
    const status = await apiService.v1GetWorkspaceKernelStatus(appStore.activeWorkspaceId)
    kernelStatus.value = String(status?.status || 'missing').toLowerCase()
    if (['ready', 'busy', 'starting'].includes(kernelStatus.value)) {
      appStore.setRuntimeError('')
    }
  } catch (error) {
    if (isUnauthorizedError(error)) {
      await handleUnauthorizedPollingError()
      return
    }
    kernelStatus.value = 'error'
    appStore.setRuntimeError(error?.response?.data?.detail || error?.message || 'Failed to fetch kernel status.')
  } finally {
    isKernelStatusRequestInFlight.value = false
  }
}

function startKernelStatusPolling() {
  if (!authStore.isAuthenticated) return
  stopKernelStatusPolling()
  refreshKernelStatus()
  kernelStatusPoller = setInterval(() => {
    if (!document.hidden && authStore.isAuthenticated) refreshKernelStatus()
  }, 5000)
}

function stopKernelStatusPolling() {
  if (kernelStatusPoller) {
    clearInterval(kernelStatusPoller)
    kernelStatusPoller = null
  }
}

async function interruptKernel() {
  if (!appStore.activeWorkspaceId || !appStore.hasWorkspace || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  try {
    const response = await apiService.v1InterruptWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) toast.success('Kernel Interrupted', 'Execution interrupt signal sent.')
    else toast.error('Interrupt Failed', 'No running kernel found.')
    await refreshKernelStatus()
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
    await refreshKernelStatus()
  } catch (error) {
    toast.error('Restart Failed', error?.response?.data?.detail || error.message)
    await refreshKernelStatus()
  } finally {
    isKernelActionRunning.value = false
  }
}

// Named handler so we can remove the exact same reference on unmount
function handleVisibilityChange() {
  if (!document.hidden && authStore.isAuthenticated && appStore.activeWorkspaceId && appStore.hasWorkspace) {
    refreshKernelStatus()
    void refreshArtifactUsage()
  }
}

function handleDocumentClick(event) {
  if (!isAccountMenuOpen.value) return
  const root = accountMenuRef.value
  if (!root) return
  if (!root.contains(event.target)) {
    isAccountMenuOpen.value = false
  }
}

function handleDocumentKeydown(event) {
  if (event.key !== 'Escape') return
  if (isTermsDialogOpen.value) {
    closeTermsDialog()
    return
  }
  if (isLogoutConfirmOpen.value) {
    cancelLogout()
    return
  }
  if (isSettingsOpen.value) {
    closeSettings()
    return
  }
  if (isAccountMenuOpen.value) {
    isAccountMenuOpen.value = false
  }
}

// Lifecycle and Watchers
onMounted(() => {
  if (authStore.isAuthenticated && appStore.activeWorkspaceId && appStore.hasWorkspace) {
    startKernelStatusPolling()
    startArtifactUsagePolling()
  }
  setupWebSocketMonitoring()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleDocumentKeydown)
})

onUnmounted(() => {
  stopKernelStatusPolling()
  stopArtifactUsagePolling()
  resetArtifactUsage()
  if (typeof unsubscribeWebSocketConnection === 'function') {
    unsubscribeWebSocketConnection()
    unsubscribeWebSocketConnection = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleDocumentKeydown)
})

watch([() => appStore.activeWorkspaceId, () => appStore.hasWorkspace, () => authStore.isAuthenticated], ([newId, hasWorkspace, isAuthenticated]) => {
  if (isAuthenticated && newId && hasWorkspace) {
    startKernelStatusPolling()
    startArtifactUsagePolling()
  } else {
    stopKernelStatusPolling()
    stopArtifactUsagePolling()
    resetArtifactUsage()
  }
})

watch(
  [() => appStore.dataframes, () => appStore.figures, () => appStore.dataframeCount, () => appStore.figureCount, () => authStore.isAuthenticated],
  () => {
    if (!authStore.isAuthenticated) return
    if (!appStore.activeWorkspaceId || !appStore.hasWorkspace) return
    scheduleArtifactUsageRefresh()
  }
)
</script>

<style scoped>
:deep(.terms-markdown-content h1),
:deep(.terms-markdown-content h2),
:deep(.terms-markdown-content h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

:deep(.terms-markdown-content h1:first-child),
:deep(.terms-markdown-content h2:first-child),
:deep(.terms-markdown-content h3:first-child) {
  margin-top: 0;
}

:deep(.terms-markdown-content p) {
  margin: 0.5rem 0;
}

:deep(.terms-markdown-content ul) {
  margin: 0.5rem 0;
  padding-left: 1.1rem;
  list-style: disc;
}

:deep(.terms-markdown-content li) {
  margin: 0.2rem 0;
}

:deep(.terms-markdown-content code) {
  background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent);
  border-radius: 0.25rem;
  padding: 0.05rem 0.3rem;
}

:deep(.terms-markdown-content a) {
  color: #2563eb;
  text-decoration: underline;
}
</style>
