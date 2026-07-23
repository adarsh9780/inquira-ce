<template>
  <div class="min-h-screen bg-[var(--color-base)] flex flex-col">
    <ToastContainer />

    <div
      v-show="!startupFailure && (!desktopStartup.ready || !modelOnboarding.checked)"
      class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]"
      role="status"
      aria-live="polite"
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
      role="alert"
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
        <div class="mt-8 rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-danger-bg)] px-4 py-3 text-left">
          <p class="text-xs font-medium uppercase tracking-wider text-[var(--color-danger-text)]">Error</p>
          <p class="mt-2 text-sm text-[var(--color-danger-text)]">{{ startupFailure }}</p>
        </div>
        <StartupFailureActions
          :message="startupRecoveryMessage"
          @restart="restartDesktopApp"
          @open-logs="openStartupLogs"
          @copy-diagnostics="copyStartupDiagnostics"
        />
      </div>
    </div>

    <FirstRunModelOnboarding
      v-if="modelOnboarding.checked && modelOnboarding.required"
      :initial-status="modelOnboarding.status"
      @complete="handleModelOnboardingComplete"
    />

    <div v-if="authStore.isAuthenticated && appBootstrap.ready && !modelOnboarding.required" class="flex flex-col h-screen">
      <div class="flex-1 flex overflow-hidden app-shell-frame relative">
        <div
          class="h-full shrink-0 app-nav-pane"
          :class="{
            'app-nav-pane-collapsed': uiStore.isSidebarCollapsed,
          }"
        >
          <UnifiedSidebar />
        </div>
        <div class="flex-1 flex flex-col overflow-hidden app-workspace-pane">
          <RightPanel />
        </div>
      </div>
      <StatusBar />
      <SettingsModal
        v-model="uiStore.isSettingsOpen"
        :initial-tab="uiStore.settingsInitialTab"
      />
      <CommandPaletteModal
        :is-open="uiStore.isCommandPaletteOpen"
        @close="uiStore.closeCommandPalette()"
      />
      <KeyboardShortcutsModal
        :is-open="uiStore.isKeyboardShortcutsOpen"
        @close="uiStore.closeKeyboardShortcuts()"
      />
    </div>

    <Teleport to="body">
      <div
        data-testid="startup-overlay"
        :data-active="blockingOverlayActive ? 'true' : 'false'"
        :aria-hidden="blockingOverlayActive ? 'false' : 'true'"
        role="status"
        aria-live="polite"
        class="layer-blocking fixed inset-0 flex items-center justify-center bg-[var(--color-base)] transition-opacity duration-300"
        :class="blockingOverlayActive ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'"
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
            <div class="relative h-8 w-8 shrink-0" aria-hidden="true">
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
import { useUiStore } from './stores/uiStore'
import { usePreferencesStore } from './stores/preferencesStore'
import { apiService } from './services/apiService'
import { modelConnectionService } from './services/modelConnectionService'
import { themeService } from './services/themeService'
import { fontService } from './services/fontService'
import { toast } from './composables/useToast'
import { extractApiErrorMessage } from './utils/apiError'
import { normalizeThemeId } from './constants/themes'
import { normalizeAppFontId, normalizeCodeFontId } from './constants/fonts'
import { matchShortcut } from './utils/keyboardShortcuts'
import logo from './assets/favicon.svg'
import UnifiedSidebar from './components/layout/UnifiedSidebar.vue'
import RightPanel from './components/layout/RightPanel.vue'
import StatusBar from './components/layout/StatusBar.vue'
import ToastContainer from './components/ui/ToastContainer.vue'
import StartupFailureActions from './components/startup/StartupFailureActions.vue'
import SettingsModal from './components/modals/SettingsModal.vue'
import CommandPaletteModal from './components/modals/CommandPaletteModal.vue'
import KeyboardShortcutsModal from './components/modals/KeyboardShortcutsModal.vue'
import FirstRunModelOnboarding from './components/onboarding/FirstRunModelOnboarding.vue'

const appStore = useAppStore()
const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}
const authStore = useAuthStore()

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
const modelOnboarding = reactive({
  checked: false,
  required: false,
  status: null,
})
const lastRuntimeErrorToast = ref('')
const activeSnapshotUserId = ref('')
const startupFailure = ref('')
const startupRecoveryMessage = ref('')
const startupTimeline = ref([])
const desktopStartupTimeline = ref([])
const startupClock = ref(Date.now())
const hasLoadedThemePreference = ref(false)
const applyingThemePreference = ref(false)
const hasLoadedFontPreference = ref(false)
const applyingFontPreference = ref(false)
const hasLoadedCodeFontPreference = ref(false)
const applyingCodeFontPreference = ref(false)
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
  return {
    scope: 'workspace',
    message: String(appBootstrap.message || '').trim() || 'Loading your workspace...',
  }
})

const startupOverlayActive = computed(() => {
  return Boolean(appBootstrap.active)
})

const blockingOverlayActive = computed(() => {
  return startupOverlayActive.value
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
  return 'Loading your workspace.'
})

const startupOverlayMessage = computed(() => {
  return String(appBootstrap.message || '').trim() || 'Restoring your account, workspace, and runtime state.'
})

const startupOverlayHint = computed(() => {
  return 'Authentication finishes first, then the authenticated workspace restore runs as its own separate phase.'
})

const startupOverlayPill = computed(() => {
  return 'Workspace restore'
})

const startupOverlayPanelTitle = computed(() => {
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

function applyDocumentTheme(themeId) {
  if (typeof document === 'undefined') return
  const normalized = normalizeThemeId(themeId)
  document.documentElement.setAttribute('data-theme', normalized)
}

function applyDocumentFont(fontId) {
  if (typeof document === 'undefined') return
  const normalized = normalizeAppFontId(fontId)
  document.documentElement.setAttribute('data-font', normalized)
}

function applyDocumentCodeFont(fontId) {
  if (typeof document === 'undefined') return
  const normalized = normalizeCodeFontId(fontId)
  document.documentElement.setAttribute('data-code-font', normalized)
}

function openGlobalDatasetPicker() {
  appStore.openDataConnectionFlow()
}

function handleAppDatasetDragOver(event) {
  if (event.defaultPrevented) return
  if (!event?.dataTransfer?.types?.includes?.('Files')) return
  event.preventDefault()
}

function handleAppDatasetDrop(event) {
  if (event.defaultPrevented) return
  const files = Array.from(event?.dataTransfer?.files || [])
  if (files.length === 0) return
  event.preventDefault()
  appStore.openDataConnectionFlow()
}

function handleGlobalShortcuts(event) {
  if (!authStore.isAuthenticated) return
  if (event.defaultPrevented) return
  if (event.repeat) return

  const hasPrimaryModifier = event.metaKey || event.ctrlKey
  if (!hasPrimaryModifier || event.altKey) return

  if (matchShortcut(event, 'conversation-tree')) {
    event.preventDefault()
    uiStore.setActiveTab('conversation-tree')
    return
  }

  if (matchShortcut(event, 'command-palette')) {
    event.preventDefault()
    uiStore.toggleCommandPalette()
    return
  }

  if (matchShortcut(event, 'settings')) {
    event.preventDefault()
    uiStore.openSettings('setup')
    return
  }

  if (matchShortcut(event, 'sidebar')) {
    event.preventDefault()
    uiStore.setSidebarCollapsed(!uiStore.isSidebarCollapsed)
    return
  }

  if (matchShortcut(event, 'schema')) {
    event.preventDefault()
    uiStore.setActiveTab('schema-editor')
    return
  }

  if (matchShortcut(event, 'dataset-import')) {
    event.preventDefault()
    void openGlobalDatasetPicker()
    return
  }

  if (matchShortcut(event, 'terminal')) {
    event.preventDefault()
    uiStore.toggleTerminal()
    return
  }

}

function handleOpenDatasetPickerRequest() {
  appStore.openDataConnectionFlow()
}

async function readDesktopStartupState() {
  if (wailsApp()?.GetStartupState) {
    try {
      return wailsApp().GetStartupState()
    } catch (error) {
      console.warn('⚠️ Failed to read desktop startup state from Go:', error)
      return {
        ready: false,
        error: 'Could not read desktop service startup state. Restart the app or open the logs for details.',
        message: '',
      }
    }
  }
  return { ready: true, error: '', message: '' }
}

async function invokeDesktopRecovery(command) {
  if (command === 'restart_desktop_app' && wailsApp()?.RestartDesktopApp) {
    await wailsApp().RestartDesktopApp()
    return
  }
  if (command === 'open_startup_logs' && wailsApp()?.OpenStartupLogs) {
    await wailsApp().OpenStartupLogs()
    return
  }
  startupRecoveryMessage.value = 'Desktop recovery actions are only available in the installed app.'
}

async function restartDesktopApp() {
  startupRecoveryMessage.value = 'Restarting desktop app...'
  await invokeDesktopRecovery('restart_desktop_app')
}

async function openStartupLogs() {
  startupRecoveryMessage.value = ''
  await invokeDesktopRecovery('open_startup_logs')
}

async function copyStartupDiagnostics() {
  try {
    await navigator.clipboard.writeText(`Inquira startup failure\n${startupFailure.value}`)
    startupRecoveryMessage.value = 'Startup diagnostics copied.'
  } catch (error) {
    startupRecoveryMessage.value = String(error?.message || 'Could not copy startup diagnostics.')
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
      closeCurrentDesktopStartupStage()
      desktopStartup.active = false
      desktopStartup.ready = true
      desktopStartup.message = ''
      return true
    }

    await new Promise((resolve) => window.setTimeout(resolve, pollDelayMs))
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
    activeSnapshotUserId.value = userId
    await appStore.loadLocalConfig(userId)
  }

  try {
    appBootstrap.message = 'Loading your account...'
    await appStore.loadUserPreferences()
    appBootstrap.message = 'Selecting your workspace...'
    await appStore.fetchWorkspaces()
    if (appStore.activeWorkspaceId) {
      appBootstrap.message = 'Loading workspace history...'
      await appStore.fetchConversations()
      if (appStore.activeConversationId) {
        await appStore.fetchConversationTurns()
      }
    }
    console.debug('Loaded workspace state for local user')
  } catch (error) {
    console.error('Failed to load v1 workspace state:', error)
  } finally {
    appBootstrap.active = false
    appBootstrap.ready = true
    appBootstrap.message = ''
  }
}

async function loadModelOnboardingStatus() {
  try {
    const status = await modelConnectionService.getOnboardingStatus()
    modelOnboarding.status = status
    modelOnboarding.required = !status?.completed
  } catch (error) {
    modelOnboarding.status = {
      completed: false,
      connection_ready: false,
      provider: 'openrouter',
      error: extractApiErrorMessage(error, 'Could not load first-run setup.'),
    }
    modelOnboarding.required = true
  } finally {
    modelOnboarding.checked = true
  }
}

function handleModelOnboardingComplete(status) {
  modelOnboarding.status = status
  modelOnboarding.required = false
  uiStore.openSettings('workspace-general')
}

watch(
  () => preferencesStore.uiTheme,
  (themeId) => {
    const normalized = normalizeThemeId(themeId)
    applyDocumentTheme(normalized)
    if (!hasLoadedThemePreference.value || applyingThemePreference.value) return
    void themeService.saveThemePreference(normalized)
  },
  { immediate: true },
)

watch(
  () => preferencesStore.uiFont,
  (fontId) => {
    const normalized = normalizeAppFontId(fontId)
    applyDocumentFont(normalized)
    if (!hasLoadedFontPreference.value || applyingFontPreference.value) return
    void fontService.saveAppFontPreference(normalized)
  },
  { immediate: true },
)

watch(
  () => preferencesStore.uiCodeFont,
  (fontId) => {
    const normalized = normalizeCodeFontId(fontId)
    applyDocumentCodeFont(normalized)
    if (!hasLoadedCodeFontPreference.value || applyingCodeFontPreference.value) return
    void fontService.saveCodeFontPreference(normalized)
  },
  { immediate: true },
)

onMounted(async () => {
  if (typeof window !== 'undefined') {
    applyingThemePreference.value = true
    applyingFontPreference.value = true
    applyingCodeFontPreference.value = true
    try {
      const [storedTheme, storedFont, storedCodeFont] = await Promise.all([
        themeService.loadThemePreference(),
        fontService.loadAppFontPreference(),
        fontService.loadCodeFontPreference(),
      ])
      preferencesStore.setUiTheme(storedTheme, { persist: false })
      preferencesStore.setUiFont(storedFont, { persist: false })
      preferencesStore.setUiCodeFont(storedCodeFont, { persist: false })
      applyDocumentTheme(storedTheme)
      applyDocumentFont(storedFont)
      applyDocumentCodeFont(storedCodeFont)
    } finally {
      applyingThemePreference.value = false
      hasLoadedThemePreference.value = true
      applyingFontPreference.value = false
      hasLoadedFontPreference.value = true
      applyingCodeFontPreference.value = false
      hasLoadedCodeFontPreference.value = true
    }
  } else {
    hasLoadedThemePreference.value = true
    hasLoadedFontPreference.value = true
    hasLoadedCodeFontPreference.value = true
  }

  startupClockTimer = window.setInterval(() => {
    startupClock.value = Date.now()
  }, 1000)
  document.addEventListener('keydown', handleGlobalShortcuts)
  document.addEventListener('dragover', handleAppDatasetDragOver)
  document.addEventListener('drop', handleAppDatasetDrop)
  window.addEventListener('inquira:open-dataset-picker', handleOpenDatasetPickerRequest)
  const startupOk = await waitForDesktopStartupReady()
  if (!startupOk) {
    return
  }

  await loadModelOnboardingStatus()

  await authStore.initialize()
  if (authStore.isAuthenticated && !appBootstrap.ready && !appBootstrap.active) {
    await handleAuthenticated(authStore.user)
  }
})

watch(
  () => appBootstrap.message,
  (message) => {
    if (!appBootstrap.active) return
    recordStartupStage('workspace', message)
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
    lastRuntimeErrorToast.value = ''
    appStore.setRuntimeError('')
  }
)

function handleAppUnload() {
  void appStore.flushLocalConfig?.()
}
window.addEventListener('beforeunload', handleAppUnload)

// Cleanup on unmount
onUnmounted(() => {
  void appStore.flushLocalConfig?.()
  if (startupClockTimer) {
    window.clearInterval(startupClockTimer)
    startupClockTimer = null
  }
  document.removeEventListener('keydown', handleGlobalShortcuts)
  document.removeEventListener('dragover', handleAppDatasetDragOver)
  document.removeEventListener('drop', handleAppDatasetDrop)
  window.removeEventListener('inquira:open-dataset-picker', handleOpenDatasetPickerRequest)
  window.removeEventListener('beforeunload', handleAppUnload)
})
</script>

<style>
.monaco-editor {
  border-radius: 0.375rem;
}

/* Backend startup overlay transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--motion-duration-slow) var(--motion-ease-standard);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.app-shell-frame {
  background-color: var(--color-shell-backdrop);
}

.app-nav-pane {
  /* App shell owns the structural sidebar rail width. */
  width: 260px;
  transition: width var(--motion-duration-slow) var(--motion-ease-spring);
  overflow: hidden;
  border-right: 1px solid var(--color-border);
  background-color: var(--color-sidebar-surface);
  box-shadow: inset -1px 0 0 color-mix(in srgb, var(--color-text-main) 4%, transparent);
}

.app-nav-pane-collapsed {
  width: 52px;
}

.app-workspace-pane {
  background-color: var(--color-workspace-surface);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--color-text-main) 3%, transparent);
}

.startup-brand-logo {
  animation: startup-logo-float 7s var(--motion-ease-standard) infinite;
  filter: drop-shadow(0 20px 32px color-mix(in srgb, var(--color-text-main) 20%, transparent));
}

/* Minimal startup screen animations */
.startup-enter {
  animation: startup-fade-in var(--motion-duration-slower) var(--motion-ease-standard) forwards;
}

.startup-logo {
  animation: startup-logo-reveal var(--motion-duration-slower) var(--motion-ease-standard) var(--motion-duration-standard) forwards;
}

.startup-text {
  opacity: 0;
  animation: startup-text-reveal var(--motion-duration-slower) var(--motion-ease-standard) calc(var(--motion-duration-standard) * 2) forwards;
}

.startup-text-delay {
  opacity: 0;
  animation: startup-text-reveal var(--motion-duration-slower) var(--motion-ease-standard) calc(var(--motion-duration-standard) * 2.75) forwards;
}

.startup-progress {
  opacity: 0;
  animation: startup-progress-reveal var(--motion-duration-slower) var(--motion-ease-standard) calc(var(--motion-duration-standard) * 3.5) forwards;
}

.startup-text-delay-2 {
  opacity: 0;
  animation: startup-text-reveal var(--motion-duration-slower) var(--motion-ease-standard) calc(var(--motion-duration-standard) * 3.25) forwards;
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
  background: color-mix(in srgb, var(--color-text-muted) 35%, transparent);
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
