<template>
  <div class="min-h-screen bg-[var(--color-base)] flex flex-col">
    <ToastContainer />

    <StartupScreen
      v-show="!startupFailure && (!desktopStartup.ready || !modelOnboarding.checked)"
      :logo="logo"
      :title="desktopStartupTitle"
      :message="desktopStartupMessage"
      :progress="progressPercent"
    />

    <StartupFailureScreen
      v-show="startupFailure"
      :logo="logo"
      :error="startupFailure"
      :recovery-message="startupRecoveryMessage"
      @restart="restartDesktopApp"
      @open-logs="openStartupLogs"
      @copy-diagnostics="copyStartupDiagnostics"
    />

    <FirstRunModelOnboarding
      v-if="modelOnboarding.checked && modelOnboarding.required"
      :initial-status="modelOnboarding.status"
      @complete="handleModelOnboardingComplete"
    />

    <AppShell
      v-if="authStore.isAuthenticated && appBootstrap.ready && !modelOnboarding.required"
      :sidebar-collapsed="uiStore.isSidebarCollapsed"
    >
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
    </AppShell>

    <BlockingOperationOverlay
      :active="blockingOverlayActive"
      :logo="logo"
      :pill="startupOverlayPill"
      :title="startupOverlayTitle"
      :message="startupOverlayMessage"
      :elapsed="currentStartupElapsedLabel"
    />
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from './stores/authStore'
import { useUiStore } from './stores/uiStore'
import { usePreferencesStore } from './stores/preferencesStore'
import { useWorkspaceStore } from './stores/workspaceStore'
import { useConversationStore } from './stores/conversationStore'
import { useExecutionStore } from './stores/executionStore'
import { useSessionSnapshot } from './composables/useSessionSnapshot'
import { useWorkspaceActivation } from './composables/useWorkspaceActivation'
import { useGlobalShortcuts } from './composables/useGlobalShortcuts'
import { useNativeDatasetDrop } from './composables/useNativeDatasetDrop'
import { modelConnectionService } from './services/modelConnectionService'
import { themeService } from './services/themeService'
import { fontService } from './services/fontService'
import { toast } from './composables/useToast'
import { extractApiErrorMessage } from './utils/apiError'
import { normalizeThemeId } from './constants/themes'
import { normalizeAppFontId, normalizeCodeFontId } from './constants/fonts'
import logo from './assets/favicon.svg'
import AppShell from './components/layout/AppShell.vue'
import ToastContainer from './components/ui/ToastContainer.vue'
import StartupScreen from './components/startup/StartupScreen.vue'
import StartupFailureScreen from './components/startup/StartupFailureScreen.vue'
import BlockingOperationOverlay from './components/startup/BlockingOperationOverlay.vue'
import CommandPaletteModal from './components/modals/CommandPaletteModal.vue'
import KeyboardShortcutsModal from './components/modals/KeyboardShortcutsModal.vue'
import FirstRunModelOnboarding from './components/onboarding/FirstRunModelOnboarding.vue'

const SettingsModal = defineAsyncComponent(() => import('./components/modals/SettingsModal.vue'))

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const executionStore = useExecutionStore()
const authStore = useAuthStore()
const sessionSnapshot = useSessionSnapshot()
const workspaceActivation = useWorkspaceActivation()
const openGlobalDatasetPicker = () => workspaceActivation.openDataConnectionFlow()
useGlobalShortcuts(computed(() => authStore.isAuthenticated), openGlobalDatasetPicker)
useNativeDatasetDrop(openGlobalDatasetPicker)
sessionSnapshot.configurePersistence()

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}
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
    sessionSnapshot.reset()
    activeSnapshotUserId.value = userId
    await sessionSnapshot.load(userId)
  }

  try {
    appBootstrap.message = 'Loading your account...'
    await preferencesStore.loadUserPreferences()
    appBootstrap.message = 'Selecting your workspace...'
    await workspaceStore.fetchWorkspaces()
    if (workspaceStore.activeWorkspaceId) {
      appBootstrap.message = 'Loading workspace history...'
      await conversationStore.fetchConversations(workspaceStore.activeWorkspaceId)
      if (conversationStore.activeConversationId) {
        await conversationStore.fetchConversationTurns()
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
  () => executionStore.runtimeError,
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
    sessionSnapshot.reset()
    lastRuntimeErrorToast.value = ''
    executionStore.setRuntimeError('')
  }
)

function handleAppUnload() {
  void sessionSnapshot.flush()
}
window.addEventListener('beforeunload', handleAppUnload)

// Cleanup on unmount
onUnmounted(() => {
  void sessionSnapshot.flush()
  if (startupClockTimer) {
    window.clearInterval(startupClockTimer)
    startupClockTimer = null
  }
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
