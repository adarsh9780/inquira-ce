<template>
  <div class="min-h-screen bg-white flex flex-col">
    <ToastContainer />

    <div
      v-show="!startupFailure && !desktopStartup.ready"
      class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]"
    >
      <div class="w-full max-w-md px-6 text-center">
        <!-- Logo -->
        <div class="flex justify-center mb-8">
          <img
            :src="logo"
            alt="Inquira logo"
            class="h-16 w-16"
          />
        </div>

        <!-- Brand -->
        <h1 class="text-2xl font-semibold tracking-tight text-[var(--color-text-main)]">
          {{ desktopStartupTitle }}
        </h1>
        <p class="mt-3 text-sm text-[var(--color-text-muted)]">
          {{ desktopStartupMessage }}
        </p>

        <!-- Progress -->
        <div class="mt-10">
          <div class="h-px w-full bg-[var(--color-border)]">
            <div
              class="h-full bg-[var(--color-text-main)] transition-all duration-500 ease-out"
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
          <div class="mt-4 flex items-center justify-center gap-2">
            <div class="h-1.5 w-1.5 rounded-full bg-[var(--color-text-muted)] animate-pulse"></div>
            <span class="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">Starting</span>
          </div>
        </div>
      </div>
    </div>

    <div
      v-show="startupFailure"
      class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]"
    >
      <div class="w-full max-w-md px-6 text-center">
        <!-- Logo -->
        <div class="flex justify-center mb-8">
          <img :src="logo" alt="Inquira logo" class="h-16 w-16" />
        </div>

        <!-- Error -->
        <h1 class="text-xl font-semibold tracking-tight text-[var(--color-text-main)]">
          Startup Failed
        </h1>
        <p class="mt-3 text-sm text-[var(--color-text-muted)]">
          The desktop services could not reach a healthy state.
        </p>

        <!-- Error details -->
        <div class="mt-8 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-left">
          <p class="text-xs font-medium uppercase tracking-wider text-red-600">Error</p>
          <p class="mt-2 text-sm text-red-800">{{ startupFailure }}</p>
        </div>
      </div>
    </div>

    <div v-show="authStore.isAuthenticated && appBootstrap.ready" class="flex flex-col h-screen">
      <ConnectionStatusIndicator />
      <div class="flex-1 flex overflow-hidden bg-white relative">
        <Transition name="sidebar-shell">
          <div v-if="!appStore.isSidebarCollapsed" class="h-full shrink-0">
            <UnifiedSidebar />
          </div>
        </Transition>
        <div class="flex-1 bg-white flex flex-col overflow-hidden">
          <RightPanel />
        </div>
      </div>
      <StatusBar />
    </div>

    <Teleport to="body">
      <div
        class="fixed inset-0 z-[9999] flex items-center justify-center bg-[var(--color-base)] transition-opacity duration-300"
        :class="(workspaceRuntimeStatus.active || appBootstrap.active) ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'"
      >
        <div class="w-full max-w-md px-6 text-center">
          <!-- Logo -->
          <div class="flex justify-center mb-6">
            <img
              :src="logo"
              alt="Inquira logo"
              class="h-16 w-16"
            />
          </div>

          <!-- Status -->
          <p class="text-xs font-medium uppercase tracking-widest text-[var(--color-text-muted)]">
            {{ startupOverlayPill }}
          </p>
          <h1 class="mt-4 text-2xl font-semibold tracking-tight text-[var(--color-text-main)]">
            {{ startupOverlayTitle }}
          </h1>
          <p class="mt-3 text-sm text-[var(--color-text-muted)]">
            {{ startupOverlayMessage }}
          </p>

          <!-- Spinner + elapsed only; keep a single status message above -->
          <div class="mt-8 flex items-center justify-center gap-3">
            <div class="relative h-8 w-8 shrink-0">
              <div class="absolute inset-0 rounded-full border-2 border-[var(--color-border)]"></div>
              <div class="absolute inset-0 rounded-full border-2 border-t-[var(--color-text-main)] border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
            </div>
            <p class="text-xs text-[var(--color-text-muted)]">
              {{ currentStartupElapsedLabel }}
            </p>
          </div>
        </div>
      </div>
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
import logo from './assets/favicon.svg'
import UnifiedSidebar from './components/layout/UnifiedSidebar.vue'
import RightPanel from './components/layout/RightPanel.vue'
import StatusBar from './components/layout/StatusBar.vue'
import ToastContainer from './components/ui/ToastContainer.vue'
import ConnectionStatusIndicator from './components/ui/ConnectionStatusIndicator.vue'

const appStore = useAppStore()
const authStore = useAuthStore()

const workspaceRuntimeStatus = reactive({
  active: false,
  message: '',
})
const appBootstrap = reactive({
  active: false,
  ready: false,
  message: '',
})
const desktopStartup = reactive({
  active: false,
  ready: false,
  message: '',
  error: '',
})
const wsUnsubscribers = ref([])
const lastRuntimeErrorToast = ref('')
const activeSnapshotUserId = ref('')
const startupFailure = ref('')
const startupTimeline = ref([])
const desktopStartupTimeline = ref([])
const startupClock = ref(Date.now())
let startupClockTimer = null
const isE2EMode = import.meta.env.VITE_E2E === '1'

const STARTUP_SCOPE_LABELS = {
  workspace: 'Workspace',
  runtime: 'Runtime',
}

function formatElapsed(ms) {
  if (!Number.isFinite(ms) || ms < 1000) return '<1s'
  if (ms < 60000) return `${Math.round(ms / 100) / 10}s`
  return `${Math.round(ms / 1000)}s`
}

function normalizeStartupMessage(message) {
  return String(message || '')
    .trim()
    .replace(/\s+/g, ' ')
}

function recordStartupStage(scope, message) {
  const rendered = String(message || '').trim()
  if (!rendered) return

  const now = Date.now()
  const canonicalMessage = normalizeStartupMessage(rendered)
  const current = startupTimeline.value[startupTimeline.value.length - 1]
  if (current?.scope === scope && current?.canonicalMessage === canonicalMessage) {
    return
  }

  const recentDuplicate = startupTimeline.value
    .slice(-4)
    .some((entry) => entry.scope === scope && entry.canonicalMessage === canonicalMessage)
  if (recentDuplicate) {
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
      canonicalMessage,
      startedAt: now,
      endedAt: 0,
    },
  ]

  console.info(`[STARTUP TRACE] ${scope}: ${rendered}`)
}

function recordDesktopStartupStage(message) {
  const rendered = String(message || '').trim()
  if (!rendered) return

  const now = Date.now()
  const current = desktopStartupTimeline.value[desktopStartupTimeline.value.length - 1]
  if (current?.message === rendered) {
    return
  }

  const recentDuplicate = desktopStartupTimeline.value
    .slice(-4)
    .some((entry) => entry.message === rendered)
  if (recentDuplicate) {
    return
  }

  if (current && !current.endedAt) {
    current.endedAt = now
  }

  desktopStartupTimeline.value = [
    ...desktopStartupTimeline.value.slice(-11),
    {
      key: `desktop:${rendered}:${now}`,
      message: rendered,
      startedAt: now,
      endedAt: 0,
    },
  ]
}

function closeCurrentDesktopStartupStage() {
  const current = desktopStartupTimeline.value[desktopStartupTimeline.value.length - 1]
  if (current && !current.endedAt) {
    current.endedAt = Date.now()
  }
}

const currentStartupStage = computed(() => {
  if (workspaceRuntimeStatus.active) {
    return {
      scope: 'runtime',
      message: String(workspaceRuntimeStatus.message || '').trim() || 'Preparing workspace runtime...',
    }
  }
  return {
    scope: 'workspace',
    message: String(appBootstrap.message || '').trim() || 'Loading your workspace...',
  }
})

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
        scope,
        elapsed: formatElapsed(endedAt - entry.startedAt),
      }
    })
})

const desktopStartupTimelineEntries = computed(() => {
  return desktopStartupTimeline.value
    .slice(-6)
    .reverse()
    .map((entry) => {
      const endedAt = entry.endedAt || startupClock.value
      return {
        key: entry.key,
        label: entry.message,
        elapsed: formatElapsed(endedAt - entry.startedAt),
      }
    })
})

const startupOverlayTitle = computed(() => {
  if (workspaceRuntimeStatus.active) return 'Preparing your workspace runtime.'
  return 'Loading your workspace.'
})

const startupOverlayMessage = computed(() => {
  if (workspaceRuntimeStatus.active) {
    return String(workspaceRuntimeStatus.message || '').trim() || 'Creating the runtime your current workspace needs.'
  }
  return String(appBootstrap.message || '').trim() || 'Restoring your account, workspace, and runtime state.'
})

const startupOverlayHint = computed(() => {
  if (workspaceRuntimeStatus.active) {
    return 'Kernel and environment work now stays visible inside the app shell instead of appearing as a detached dialog.'
  }
  return 'Authentication finishes first, then the authenticated workspace restore runs as its own separate phase.'
})

const startupOverlayPill = computed(() => {
  if (workspaceRuntimeStatus.active) return 'Workspace runtime'
  if (appBootstrap.active) return 'Workspace restore'
  return 'Workspace restore'
})

const startupOverlayPanelTitle = computed(() => {
  if (workspaceRuntimeStatus.active) return 'Workspace progress'
  return 'Workspace handoff'
})

const desktopStartupTitle = computed(() => {
  if (!desktopStartup.ready) return 'Starting Inquira.'
  return 'Preparing the app.'
})

const desktopStartupMessage = computed(() => {
  return String(desktopStartup.message || '').trim() || 'Launching desktop services and verifying the runtime before auth begins.'
})

const desktopStartupPanelTitle = computed(() => {
  return desktopStartup.active ? 'Desktop boot' : 'Desktop status'
})

const desktopStartupPanelHint = computed(() => {
  return desktopStartup.active
    ? 'This screen appears immediately and stays visible while the launcher bootstraps the backend.'
    : 'The startup state stays available here until the auth shell is ready.'
})

const progressPercent = computed(() => {
  const total = desktopStartupTimeline.value.length
  if (total === 0) return 0
  const completed = desktopStartupTimeline.value.filter(e => e.status === 'completed').length
  return Math.round((completed / total) * 100)
})

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

async function readDesktopStartupState() {
  if (typeof window === 'undefined' || !window.__TAURI_INTERNALS__) {
    return { ready: true, error: '', message: '' }
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    return await invoke('get_startup_state')
  } catch (error) {
    console.warn('⚠️ Failed to read desktop startup state from Tauri:', error)
    return { ready: true, error: '', message: '' }
  }
}

async function subscribeDesktopStartupEvents(onMessage) {
  if (typeof window === 'undefined' || !window.__TAURI_INTERNALS__) {
    return () => {}
  }

  try {
    const { listen } = await import('@tauri-apps/api/event')
    const unlisten = await listen('backend-status', (event) => {
      const payload = String(event?.payload || '').trim()
      if (!payload || payload.toLowerCase() === 'ready') return
      onMessage(payload)
    })
    return () => {
      try {
        unlisten()
      } catch (_error) {}
    }
  } catch (error) {
    console.warn('⚠️ Failed to subscribe to desktop startup status events:', error)
    return () => {}
  }
}

async function waitForDesktopStartupReady() {
  desktopStartup.active = true
  desktopStartup.ready = false
  desktopStartup.error = ''
  desktopStartup.message = 'Launching desktop services...'
  desktopStartupTimeline.value = []
  recordDesktopStartupStage(desktopStartup.message)

  const pollDelayMs = 250
  const stopDesktopStatusListener = await subscribeDesktopStartupEvents((message) => {
    desktopStartup.message = message
    recordDesktopStartupStage(message)
  })

  try {
    while (true) {
      const state = await readDesktopStartupState()
      const message = String(state?.message || '').trim()
      if (message) {
        desktopStartup.message = message
        recordDesktopStartupStage(desktopStartup.message)
      }
      desktopStartup.error = String(state?.error || '').trim()

      if (desktopStartup.error) {
        closeCurrentDesktopStartupStage()
        startupFailure.value = desktopStartup.error
        desktopStartup.active = false
        desktopStartup.ready = false
        return false
      }

      if (state?.ready) {
        desktopStartup.message = 'Waiting for backend API...'
        recordDesktopStartupStage(desktopStartup.message)
        try {
          await apiService.waitForBackendReady()
        } catch (error) {
          const detail = String(error?.message || 'Backend did not become ready in time.').trim()
          desktopStartup.error = detail
          closeCurrentDesktopStartupStage()
          startupFailure.value = detail
          desktopStartup.active = false
          desktopStartup.ready = false
          return false
        }
        closeCurrentDesktopStartupStage()
        desktopStartup.active = false
        desktopStartup.ready = true
        desktopStartup.message = ''
        return true
      }

      await new Promise((resolve) => window.setTimeout(resolve, pollDelayMs))
    }
  } finally {
    stopDesktopStatusListener()
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
  if (isE2EMode) {
    void settingsWebSocket.connectPersistent(userId).catch((wsError) => {
      console.error('❌ Failed to establish persistent WebSocket connection:', wsError)
    })
  } else {
    try {
      await settingsWebSocket.connectPersistent(userId)
    } catch (wsError) {
      console.error('❌ Failed to establish persistent WebSocket connection:', wsError)
    }
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
    if (!isE2EMode) {
      walkthroughService.startIfFirstTime()
    }
  } catch (error) {
    console.error('Failed to load v1 workspace state:', error)
  } finally {
    appBootstrap.active = false
    appBootstrap.ready = true
    appBootstrap.message = ''
  }
}

function handleAuthClose() {
  console.debug('Auth modal closed without authentication')
}

onMounted(async () => {
  startupClockTimer = window.setInterval(() => {
    startupClock.value = Date.now()
  }, 1000)
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

  const startupOk = await waitForDesktopStartupReady()
  if (!startupOk) {
    return
  }

  void authStore.initialize()
})

watch(
  () => appBootstrap.message,
  (message) => {
    if (!appBootstrap.active) return
    if (workspaceRuntimeStatus.active) return
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
    desktopStartup.active = false
    desktopStartup.ready = true
    desktopStartup.message = ''
    desktopStartup.error = ''
    desktopStartupTimeline.value = []
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

.startup-brand-logo {
  animation: startup-logo-float 7s ease-in-out infinite;
  filter: drop-shadow(0 20px 32px rgba(24, 24, 27, 0.2));
}

/* Minimal startup screen animations */
.startup-enter {
  animation: startup-fade-in 0.6s ease-out forwards;
}

.startup-logo {
  animation: startup-logo-reveal 0.8s ease-out 0.2s forwards;
}

.startup-text {
  opacity: 0;
  animation: startup-text-reveal 0.6s ease-out 0.4s forwards;
}

.startup-text-delay {
  opacity: 0;
  animation: startup-text-reveal 0.6s ease-out 0.55s forwards;
}

.startup-progress {
  opacity: 0;
  animation: startup-progress-reveal 0.6s ease-out 0.7s forwards;
}

.startup-text-delay-2 {
  opacity: 0;
  animation: startup-text-reveal 0.6s ease-out 0.65s forwards;
}

@keyframes startup-fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes startup-logo-reveal {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes startup-text-reveal {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes startup-progress-reveal {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.startup-progress-scroll,
.desktop-startup-progress-scroll {
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.startup-progress-scroll::-webkit-scrollbar,
.desktop-startup-progress-scroll::-webkit-scrollbar {
  width: 10px;
}

.startup-progress-scroll::-webkit-scrollbar-thumb,
.desktop-startup-progress-scroll::-webkit-scrollbar-thumb {
  background: rgba(113, 113, 122, 0.35);
  border-radius: 999px;
}

@keyframes startup-logo-float {
  0%,
  100% {
    transform: translateY(0px) scale(1);
  }
  50% {
    transform: translateY(-8px) scale(1.02);
  }
}
</style>
