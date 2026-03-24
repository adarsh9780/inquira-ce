<template>
  <div class="min-h-screen bg-white flex flex-col">
    <ToastContainer />

    <ConnectionStatusIndicator v-if="authStore.isAuthenticated && appBootstrap.ready" />

    <AuthModal
      v-if="!startupFailure && !authStore.isAuthenticated"
      :is-open="true"
      @close="handleAuthClose"
    />

    <div
      v-else-if="startupFailure"
      class="fixed inset-0 overflow-y-auto bg-[var(--color-base)]"
    >
      <div class="relative min-h-screen overflow-hidden px-4 py-6 sm:px-6 lg:px-8">
        <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.08),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(24,24,27,0.08),_transparent_34%)]"></div>
        <div class="absolute inset-x-0 top-0 h-64 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(253,252,248,0))]"></div>
        <div class="relative mx-auto flex min-h-[calc(100vh-3rem)] max-w-3xl items-center justify-center">
          <section class="w-full overflow-hidden rounded-[2rem] border border-[var(--color-border)] bg-white/88 shadow-[0_28px_90px_rgba(24,24,27,0.1)] backdrop-blur-xl">
            <div class="p-8 sm:p-10">
              <div class="flex items-center gap-4">
                <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/70 bg-white/90 shadow-[0_16px_32px_rgba(24,24,27,0.08)]">
                  <img :src="logo" alt="Inquira logo" class="h-10 w-10 rounded-xl shadow-sm" />
                </div>
                <div>
                  <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--color-text-muted)]">Inquira startup</p>
                  <p class="mt-1 text-sm text-[var(--color-text-muted)]">Desktop startup failed</p>
                </div>
              </div>

              <div class="mt-10">
                <p class="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
                  Startup blocked
                </p>
                <h1 class="mt-4 text-4xl font-semibold tracking-[-0.05em] text-[var(--color-text-main)] sm:text-5xl">
                  Inquira could not finish starting.
                </h1>
                <p class="mt-5 text-base leading-7 text-[var(--color-text-muted)] sm:text-lg sm:leading-8">
                  The desktop services did not reach a healthy state, so the auth shell never started.
                </p>
              </div>

              <div class="mt-8 rounded-[1.5rem] border border-red-200 bg-red-50 px-5 py-5 text-red-800">
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-red-600">Startup Error</p>
                <p class="mt-3 text-sm leading-6">{{ startupFailure }}</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <div v-else-if="authStore.isAuthenticated && appBootstrap.ready" class="flex flex-col h-screen">
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
      <Transition name="fade">
        <div
          v-if="workspaceRuntimeStatus.active || appBootstrap.active"
          class="fixed inset-0 z-[9999] overflow-y-auto bg-[var(--color-base)]"
        >
          <div class="relative min-h-screen overflow-hidden px-4 py-6 sm:px-6 lg:px-8">
            <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.08),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(24,24,27,0.08),_transparent_34%)]"></div>
            <div class="absolute inset-x-0 top-0 h-64 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(253,252,248,0))]"></div>
            <div class="startup-grid absolute inset-0 opacity-70"></div>

            <div class="relative mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl items-center justify-center">
              <section class="w-full overflow-hidden rounded-[2rem] border border-[var(--color-border)] bg-white/88 shadow-[0_28px_90px_rgba(24,24,27,0.1)] backdrop-blur-xl">
                <div class="grid lg:grid-cols-[1.04fr_0.96fr]">
                  <aside class="relative overflow-hidden border-b border-[var(--color-border)] px-6 py-8 sm:px-8 lg:border-b-0 lg:border-r lg:px-10 lg:py-10">
                    <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(253,252,248,0.84)),linear-gradient(135deg,rgba(59,130,246,0.05),rgba(24,24,27,0.05))]"></div>
                    <div class="absolute -left-16 top-10 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.18),rgba(59,130,246,0))]"></div>
                    <div class="absolute bottom-12 right-[-3rem] h-56 w-56 rounded-full bg-[radial-gradient(circle,rgba(24,24,27,0.12),rgba(24,24,27,0))]"></div>

                    <div class="relative flex h-full flex-col">
                      <div class="flex items-center gap-4">
                        <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/70 bg-white/90 shadow-[0_16px_32px_rgba(24,24,27,0.08)]">
                          <img :src="logo" alt="Inquira logo" class="h-10 w-10 rounded-xl shadow-sm" />
                        </div>

                        <div>
                          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--color-text-muted)]">Inquira workspace</p>
                          <p class="mt-1 text-sm text-[var(--color-text-muted)]">{{ startupOverlayPill }}</p>
                        </div>
                      </div>

                      <div class="mt-10 max-w-xl">
                        <p class="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
                          Restoring your workspace
                        </p>
                        <h1 class="mt-4 text-4xl font-semibold tracking-[-0.05em] text-[var(--color-text-main)] sm:text-5xl lg:text-[3.5rem] lg:leading-[1.02]">
                          {{ startupOverlayTitle }}
                        </h1>
                        <p class="mt-5 max-w-lg text-base leading-7 text-[var(--color-text-muted)] sm:text-lg sm:leading-8">
                          {{ startupOverlayMessage }}
                        </p>
                      </div>

                      <div class="mt-8 rounded-[1.5rem] border border-white/70 bg-white/75 p-5 shadow-[0_20px_45px_rgba(24,24,27,0.08)]">
                        <div class="flex items-center justify-between gap-4">
                          <div>
                            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-text-muted)]">
                              Current process
                            </p>
                            <p class="mt-3 text-base font-medium text-[var(--color-text-main)] sm:text-lg">
                              {{ currentStartupProcess }}
                            </p>
                            <p class="mt-2 text-sm text-[var(--color-text-muted)]">
                              {{ currentStartupElapsedLabel }}
                            </p>
                          </div>
                          <div class="relative h-16 w-16 shrink-0">
                            <div class="absolute inset-0 rounded-full border-4 border-zinc-200"></div>
                            <div class="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
                          </div>
                        </div>
                      </div>

                      <ul class="mt-8 grid gap-3 text-sm sm:grid-cols-3 lg:mt-auto lg:grid-cols-1 xl:grid-cols-3">
                        <li class="rounded-[1.35rem] border border-white/75 bg-white/72 px-4 py-4 shadow-[0_14px_30px_rgba(24,24,27,0.06)]">
                          <p class="text-sm font-semibold text-[var(--color-text-main)]">Visible progress</p>
                          <p class="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">Workspace restore stays visible until the authenticated shell is ready to render.</p>
                        </li>
                        <li class="rounded-[1.35rem] border border-white/75 bg-white/72 px-4 py-4 shadow-[0_14px_30px_rgba(24,24,27,0.06)]">
                          <p class="text-sm font-semibold text-[var(--color-text-main)]">Real timing</p>
                          <p class="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">You can now see which step is actually consuming the time.</p>
                        </li>
                        <li class="rounded-[1.35rem] border border-white/75 bg-white/72 px-4 py-4 shadow-[0_14px_30px_rgba(24,24,27,0.06)]">
                          <p class="text-sm font-semibold text-[var(--color-text-main)]">Fewer false starts</p>
                          <p class="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{{ startupOverlayHint }}</p>
                        </li>
                      </ul>
                    </div>
                  </aside>

                  <div class="flex items-center px-6 py-8 sm:px-8 lg:px-10 lg:py-10">
                    <div class="mx-auto w-full max-w-xl rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[0_18px_48px_rgba(24,24,27,0.08)] sm:p-8">
                      <p class="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-text-muted)]">Recent stages</p>
                      <h2 class="mt-4 text-3xl tracking-[-0.04em] text-[var(--color-text-main)] sm:text-4xl">
                        {{ startupOverlayPanelTitle }}
                      </h2>
                      <p class="mt-4 text-base leading-7 text-[var(--color-text-muted)]">
                        {{ startupOverlayHint }}
                      </p>

                      <div class="mt-8 space-y-3">
                        <div
                          v-for="entry in startupTimelineEntries"
                          :key="entry.key"
                          class="flex items-start justify-between gap-4 rounded-[1.25rem] border border-zinc-200 bg-[var(--color-base)] px-4 py-4"
                        >
                          <div class="min-w-0 flex-1">
                            <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ entry.label }}</p>
                            <p class="mt-1 text-sm text-[var(--color-text-muted)]">{{ entry.elapsed }}</p>
                          </div>
                          <span class="mt-1 inline-flex rounded-full border border-zinc-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                            {{ entry.scope }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
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
import { toast } from './composables/useToast'
import logo from './assets/favicon.svg'
import AuthModal from './components/modals/AuthModal.vue'
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
const wsUnsubscribers = ref([])
const lastRuntimeErrorToast = ref('')
const activeSnapshotUserId = ref('')
const startupFailure = ref('')
const startupTimeline = ref([])
const startupClock = ref(Date.now())
let startupClockTimer = null

const STARTUP_SCOPE_LABELS = {
  workspace: 'Workspace',
  runtime: 'Runtime',
}

function formatElapsed(ms) {
  if (!Number.isFinite(ms) || ms < 1000) return '<1s'
  if (ms < 60000) return `${Math.round(ms / 100) / 10}s`
  return `${Math.round(ms / 1000)}s`
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
  return {
    scope: 'workspace',
    message: String(appBootstrap.message || '').trim() || 'Loading your workspace...',
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
        scope,
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

async function readDesktopStartupState() {
  if (typeof window === 'undefined' || !window.__TAURI_INTERNALS__) {
    return { ready: true, error: '' }
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    return await invoke('get_startup_state')
  } catch (error) {
    console.warn('⚠️ Failed to read desktop startup state from Tauri:', error)
    return { ready: true, error: '' }
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

  const startupState = await readDesktopStartupState()
  const startupError = String(startupState?.error || '').trim()
  if (startupError) {
    startupFailure.value = startupError
    return
  }

  void authStore.initialize()
})

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
