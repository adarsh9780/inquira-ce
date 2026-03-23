<template>
  <div class="min-h-screen bg-white flex flex-col">
    <!-- Toast Notifications -->
    <ToastContainer />

    <!-- Connection Status Indicator -->
    <ConnectionStatusIndicator />

    <!-- Authentication Modal -->
    <!-- Auth Modal -->
    <AuthModal
      :is-open="isAuthUiReady && authStore.initialSessionResolved && !authStore.isAuthenticated && !appBootstrap.active"
      @close="handleAuthClose"
    />

    <!-- Main App (only shown when authenticated) -->
    <div v-if="authStore.isAuthenticated && appBootstrap.ready" class="flex flex-col h-screen">
      <!-- Main Content Area with Sidebar -->
      <div class="flex-1 flex overflow-hidden bg-white relative">
        <Transition name="sidebar-shell">
          <div v-if="!appStore.isSidebarCollapsed" class="h-full shrink-0">
            <UnifiedSidebar />
          </div>
        </Transition>

        <!-- Single Panel - Tabs include Chat -->
        <div class="flex-1 bg-white flex flex-col overflow-hidden">
          <RightPanel />
        </div>
      </div>
      
      <!-- Footer Status Bar -->
      <StatusBar />
    </div>

    <!-- Backend Status Overlay ... -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="backendStatus.active || workspaceRuntimeStatus.active || appBootstrap.active"
          class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm"
        >
          <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">
            <div class="relative mx-auto mb-6 w-16 h-16">
              <div class="absolute inset-0 rounded-full border-4 border-gray-200"></div>
              <div class="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {{ workspaceRuntimeStatus.active ? 'Preparing Workspace Runtime' : appBootstrap.active ? 'Loading Your Workspace' : 'Setting up Inquira' }}
            </h3>
            <p class="text-sm text-gray-500 mb-4">{{ workspaceRuntimeStatus.active ? workspaceRuntimeStatus.message : appBootstrap.active ? appBootstrap.message : backendStatus.message }}</p>
            <p class="text-xs text-gray-400">
              {{ workspaceRuntimeStatus.active ? 'Creating virtual environment and kernel...' : appBootstrap.active ? 'Authenticating, selecting your workspace, and starting its runtime...' : 'This only happens once' }}
            </p>
            <div class="mt-5 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-left">
              <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-500">Current process</p>
              <p class="mt-2 text-sm font-medium text-gray-900">{{ currentStartupProcess }}</p>
              <p class="mt-1 text-xs text-gray-500">{{ currentStartupElapsedLabel }}</p>
              <ul v-if="startupTimelineEntries.length > 1" class="mt-3 space-y-2">
                <li
                  v-for="entry in startupTimelineEntries"
                  :key="entry.key"
                  class="flex items-start justify-between gap-4 text-xs text-gray-600"
                >
                  <span class="min-w-0 flex-1">{{ entry.label }}</span>
                  <span class="shrink-0 font-medium text-gray-500">{{ entry.elapsed }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useAppStore } from './stores/appStore'
import { useAuthStore } from './stores/authStore'
import { settingsWebSocket } from './services/websocketService'
import { previewService } from './services/previewService'
import { walkthroughService } from './services/walkthroughService'
import { apiService } from './services/apiService'
import { toast } from './composables/useToast'
import AuthModal from './components/modals/AuthModal.vue'
import UnifiedSidebar from './components/layout/UnifiedSidebar.vue'
import RightPanel from './components/layout/RightPanel.vue'
import StatusBar from './components/layout/StatusBar.vue'
import ToastContainer from './components/ui/ToastContainer.vue'
import ConnectionStatusIndicator from './components/ui/ConnectionStatusIndicator.vue'

const appStore = useAppStore()
const authStore = useAuthStore()

// Backend status (for Tauri first-launch setup)
const backendStatus = reactive({
  active: false,
  message: 'Starting backend...'
})
const workspaceRuntimeStatus = reactive({
  active: false,
  message: '',
})
const appBootstrap = reactive({
  active: false,
  ready: false,
  message: '',
})
const wsUnsubscribers = ref([])
const lastRuntimeErrorToast = ref('')
const activeSnapshotUserId = ref('')
const isAuthUiReady = ref(false)
let backendRecoveryPromise = null
const startupTimeline = ref([])
const startupClock = ref(Date.now())
let startupClockTimer = null

const BACKEND_STATUS_LABELS = {
  'agent-starting': 'Starting agent runtime...',
  'backend-starting': 'Starting API backend...',
  'health-checking': 'Checking local service health...',
  ready: 'Backend ready.',
}

const STARTUP_SCOPE_LABELS = {
  auth: 'Auth',
  desktop: 'Desktop',
  workspace: 'Workspace',
  runtime: 'Runtime',
}

function formatElapsed(ms) {
  if (!Number.isFinite(ms) || ms < 1000) return '<1s'
  if (ms < 60000) return `${Math.round(ms / 100) / 10}s`
  return `${Math.round(ms / 1000)}s`
}

function describeBackendStatus(message) {
  const normalized = String(message || '').trim()
  if (!normalized) return 'Waiting for backend startup...'
  return BACKEND_STATUS_LABELS[normalized] || normalized
}

function recordStartupStage(scope, message) {
  const rendered = String(message || '').trim()
  if (!rendered) return

  const now = Date.now()
  const current = startupTimeline.value[startupTimeline.value.length - 1]
  if (current?.scope === scope && current?.message === rendered) {
    return
  }

  if (current && !current.endedAt) {
    current.endedAt = now
  }

  startupTimeline.value = [
    ...startupTimeline.value.slice(-7),
    {
      key: `${scope}:${rendered}:${now}`,
      scope,
      message: rendered,
      startedAt: now,
      endedAt: 0,
    },
  ]

  console.info(`[STARTUP TRACE] ${scope}: ${rendered}`)
}

const currentStartupStage = computed(() => {
  if (workspaceRuntimeStatus.active) {
    return {
      scope: 'runtime',
      message: String(workspaceRuntimeStatus.message || '').trim() || 'Preparing workspace runtime...',
    }
  }
  if (appBootstrap.active) {
    return {
      scope: 'workspace',
      message: String(appBootstrap.message || '').trim() || 'Loading your workspace...',
    }
  }
  if (authStore.authFlowStage && !authStore.isAuthenticated) {
    return {
      scope: 'auth',
      message: String(authStore.authFlowMessage || '').trim() || 'Completing secure sign-in...',
    }
  }
  return {
    scope: 'desktop',
    message: describeBackendStatus(backendStatus.message),
  }
})

const currentStartupProcess = computed(() => currentStartupStage.value.message)

const currentStartupElapsedLabel = computed(() => {
  const current = startupTimeline.value[startupTimeline.value.length - 1]
  if (!current) return 'Waiting for first startup checkpoint...'
  const elapsed = (current.endedAt || startupClock.value) - current.startedAt
  return `${STARTUP_SCOPE_LABELS[current.scope] || 'Stage'} running for ${formatElapsed(elapsed)}`
})

const startupTimelineEntries = computed(() => {
  return startupTimeline.value
    .slice(-4)
    .map((entry) => {
      const endedAt = entry.endedAt || startupClock.value
      const scope = STARTUP_SCOPE_LABELS[entry.scope] || 'Stage'
      return {
        key: entry.key,
        label: `${scope}: ${entry.message}`,
        elapsed: formatElapsed(endedAt - entry.startedAt),
      }
    })
})

function markBackendReady() {
  backendStatus.active = false
  backendStatus.message = ''
  isAuthUiReady.value = true
}

async function recoverBackendReadiness() {
  if (backendRecoveryPromise) return backendRecoveryPromise

  backendRecoveryPromise = (async () => {
    while (!isAuthUiReady.value) {
      try {
        await apiService.waitForBackendReady(2000)
        markBackendReady()
        return true
      } catch (_error) {
        await new Promise((resolve) => setTimeout(resolve, 1000))
      }
    }
    return true
  })().finally(() => {
    backendRecoveryPromise = null
  })

  return backendRecoveryPromise
}

function toggleSidebarVisibility() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function handleGlobalShortcuts(event) {
  if (!authStore.isAuthenticated) return
  if (event.defaultPrevented) return
  if (event.repeat) return

  const key = String(event.key || '').toLowerCase()
  const hasPrimaryModifier = event.metaKey || event.ctrlKey
  if (!hasPrimaryModifier || event.altKey) return

  if (key === 'b') {
    event.preventDefault()
    toggleSidebarVisibility()
    return
  }

  if (key === 'j') {
    event.preventDefault()
    appStore.toggleTerminal()
    return
  }

  if (key === 'd' && event.shiftKey) {
    event.preventDefault()
    appStore.toggleDataFocusMode()
  }
}

// Listen for Tauri backend-status events (if running in Tauri)
function setupTauriListener() {
  if (window.__TAURI_INTERNALS__) {
    import('@tauri-apps/api/event').then(({ listen }) => {
      listen('backend-status', (event) => {
        if (event.payload === 'ready') {
          markBackendReady()
        } else {
          backendStatus.active = true
          backendStatus.message = event.payload
        }
      })
    })
  }
}

async function handleAuthenticated(userData) {
  const userId = String(userData?.user_id || '').trim()
  if (!userId) return

  appBootstrap.active = true
  appBootstrap.ready = false
  appBootstrap.message = 'Loading your account...'

  if (activeSnapshotUserId.value !== userId) {
    appStore.resetForAuthBoundary()
    previewService.clearSchemaCache()
    activeSnapshotUserId.value = userId
    await appStore.loadLocalConfig(userId)
  }

  // Establish persistent WebSocket connection
  try {
    await settingsWebSocket.connectPersistent(userId)
  } catch (wsError) {
    console.error('❌ Failed to establish persistent WebSocket connection:', wsError)
  }

  // Load v1 workspace/chat state
  try {
    appBootstrap.message = 'Loading your account...'
    await appStore.loadUserPreferences()
    appBootstrap.message = 'Selecting your workspace...'
    await appStore.fetchWorkspaces()
    if (appStore.activeWorkspaceId) {
      appBootstrap.message = 'Starting your workspace runtime...'
      await appStore.ensureWorkspaceKernelConnected(appStore.activeWorkspaceId)
      appBootstrap.message = 'Loading workspace history...'
      await appStore.fetchConversations()
      if (appStore.activeConversationId) {
        await appStore.fetchConversationTurns({ reset: true })
      }
    }
    console.debug('Loaded v1 workspace state for authenticated user')
    walkthroughService.startIfFirstTime()
  } catch (error) {
    console.error('Failed to load v1 workspace state:', error)
  } finally {
    appBootstrap.active = false
    appBootstrap.ready = true
    appBootstrap.message = ''
  }
}

function handleAuthClose() {
  // If user tries to close auth modal without authenticating,
  // we could show a message or just keep it open
  console.debug('Auth modal closed without authentication')
}

onMounted(async () => {
  setupTauriListener()
  startupClockTimer = window.setInterval(() => {
    startupClock.value = Date.now()
  }, 1000)
  backendStatus.active = true
  backendStatus.message = 'Starting local desktop services...'
  recordStartupStage('desktop', describeBackendStatus(backendStatus.message))
  document.addEventListener('keydown', handleGlobalShortcuts)
  wsUnsubscribers.value.push(
    settingsWebSocket.subscribeProgress((data) => {
      const stage = String(data?.stage || '')
      if (!stage.startsWith('workspace_runtime')) return
      workspaceRuntimeStatus.active = true
      workspaceRuntimeStatus.message = data?.message || 'Preparing workspace runtime...'
    }),
  )
  wsUnsubscribers.value.push(
    settingsWebSocket.subscribeComplete((result) => {
      if (!result || !result.workspace_id) return
      workspaceRuntimeStatus.active = false
      workspaceRuntimeStatus.message = ''
    }),
  )
  wsUnsubscribers.value.push(
    settingsWebSocket.subscribeError((message) => {
      if (!authStore.isAuthenticated) return
      appStore.setRuntimeError(message || 'Workspace runtime bootstrap failed.')
      if (!workspaceRuntimeStatus.active) return
      workspaceRuntimeStatus.active = false
      workspaceRuntimeStatus.message = message || ''
    }),
  )
  try {
    await apiService.waitForBackendReady()
    markBackendReady()
  } catch (error) {
    console.error('❌ Error during app initialization:', error)
    backendStatus.active = true
    backendStatus.message = 'Backend is taking longer than expected to start.'
    void recoverBackendReadiness()
  }
})

watch(
  () => backendStatus.message,
  (message) => {
    if (!backendStatus.active) return
    recordStartupStage('desktop', describeBackendStatus(message))
  },
)

watch(
  () => appBootstrap.message,
  (message) => {
    if (!appBootstrap.active) return
    recordStartupStage('workspace', message)
  },
)

watch(
  () => workspaceRuntimeStatus.message,
  (message) => {
    if (!workspaceRuntimeStatus.active) return
    recordStartupStage('runtime', message)
  },
)

watch(
  () => [authStore.authFlowStage, authStore.authFlowMessage],
  ([stage, message]) => {
    if (!stage || authStore.isAuthenticated) return
    recordStartupStage('auth', message || stage)
  },
)

watch(
  () => authStore.userId,
  async (newUserId, oldUserId) => {
    if (!newUserId || newUserId === oldUserId) return
    await handleAuthenticated(authStore.user)
  },
)

watch(
  () => appStore.runtimeError,
  (message) => {
    if (!authStore.isAuthenticated) return
    const normalized = String(message || '').trim()
    if (!normalized) return
    if (normalized === lastRuntimeErrorToast.value) return
    lastRuntimeErrorToast.value = normalized
    toast.error('Workspace Runtime Error', normalized)
  }
)

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) return
    activeSnapshotUserId.value = ''
    appBootstrap.active = false
    appBootstrap.ready = false
    appBootstrap.message = ''
    appStore.resetForAuthBoundary()
    previewService.clearSchemaCache()
    if (settingsWebSocket.isPersistentMode) {
      settingsWebSocket.disconnectPersistent()
    }
    lastRuntimeErrorToast.value = ''
    appStore.setRuntimeError('')
  }
)

// Warn user about data loss on refresh/close when data is loaded
function handleBeforeUnload(e) {
  void appStore.flushLocalConfig?.()
  if (appStore.dataFilePath) {
    e.preventDefault()
    e.returnValue = '' // Required for Chrome
  }
}
window.addEventListener('beforeunload', handleBeforeUnload)

// Cleanup on unmount
onUnmounted(() => {
  void appStore.flushLocalConfig?.()
  if (startupClockTimer) {
    window.clearInterval(startupClockTimer)
    startupClockTimer = null
  }
  document.removeEventListener('keydown', handleGlobalShortcuts)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  // Disconnect persistent WebSocket connection
  if (settingsWebSocket.isPersistentMode) {
    console.debug('🧹 Cleaning up persistent WebSocket connection')
    settingsWebSocket.disconnectPersistent()
  }
  wsUnsubscribers.value.forEach((fn) => {
    try { fn() } catch (_error) { }
  })
  wsUnsubscribers.value = []
})
</script>

<style>
.monaco-editor {
  border-radius: 0.375rem;
}

/* Backend startup overlay transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.sidebar-shell-enter-active,
.sidebar-shell-leave-active {
  transition: width 0.24s ease, opacity 0.2s ease;
  overflow: hidden;
}
.sidebar-shell-enter-from,
.sidebar-shell-leave-to {
  width: 0;
  opacity: 0;
}
.sidebar-shell-enter-to,
.sidebar-shell-leave-from {
  width: 16rem;
  opacity: 1;
}
</style>
