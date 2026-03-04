<template>
  <div class="min-h-screen bg-white flex flex-col">
    <!-- Toast Notifications -->
    <ToastContainer />

    <!-- Connection Status Indicator -->
    <ConnectionStatusIndicator />

    <!-- Authentication Modal -->
    <!-- Auth Modal -->
    <AuthModal
      :is-open="!authStore.isAuthenticated"
      @close="handleAuthClose"
      @authenticated="handleAuthenticated"
    />

    <!-- Main App (only shown when authenticated) -->
    <div v-if="authStore.isAuthenticated" class="flex flex-col h-screen">
      <!-- Main Content Area with Sidebar -->
      <div class="flex-1 flex overflow-hidden bg-white relative">
        <Transition name="sidebar-shell">
          <div v-if="!appStore.isSidebarCollapsed" class="h-full shrink-0">
            <UnifiedSidebar />
          </div>
        </Transition>

        <button
          v-if="appStore.isSidebarCollapsed"
          @click="toggleSidebarVisibility"
          class="absolute left-0 top-1/2 -translate-y-1/2 z-40 h-12 w-7 rounded-r-md border border-l-0 flex items-center justify-center transition-colors hover:bg-zinc-100/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/60"
          style="background-color: var(--color-base); border-color: var(--color-border); color: var(--color-text-muted);"
          title="Show sidebar"
          aria-label="Show sidebar"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <rect x="2.5" y="3.5" width="4" height="13" rx="1.2" stroke="currentColor" stroke-width="1.4" />
            <path d="M9 5.5H16.5M9 10H16.5M9 14.5H16.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
          </svg>
        </button>

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
          v-if="backendStatus.active || workspaceRuntimeStatus.active"
          class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm"
        >
          <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">
            <div class="relative mx-auto mb-6 w-16 h-16">
              <div class="absolute inset-0 rounded-full border-4 border-gray-200"></div>
              <div class="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {{ workspaceRuntimeStatus.active ? 'Preparing Workspace Runtime' : 'Setting up Inquira' }}
            </h3>
            <p class="text-sm text-gray-500 mb-4">{{ workspaceRuntimeStatus.active ? workspaceRuntimeStatus.message : backendStatus.message }}</p>
            <p class="text-xs text-gray-400">
              {{ workspaceRuntimeStatus.active ? 'Creating virtual environment and kernel...' : 'This only happens once' }}
            </p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useAppStore } from './stores/appStore'
import { useAuthStore } from './stores/authStore'
import { settingsWebSocket } from './services/websocketService'
import { previewService } from './services/previewService'
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
const wsUnsubscribers = ref([])
const lastRuntimeErrorToast = ref('')
const activeSnapshotUserId = ref('')

function toggleSidebarVisibility() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

// Listen for Tauri backend-status events (if running in Tauri)
function setupTauriListener() {
  if (window.__TAURI_INTERNALS__) {
    import('@tauri-apps/api/event').then(({ listen }) => {
      listen('backend-status', (event) => {
        if (event.payload === 'ready') {
          backendStatus.active = false
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
    await authStore.refreshPlan()
    await appStore.fetchWorkspaces()
    await appStore.loadUserPreferences()
    if (appStore.activeWorkspaceId) {
      await appStore.fetchConversations()
      if (appStore.activeConversationId) {
        await appStore.fetchConversationTurns({ reset: true })
      }
    }
    console.debug('Loaded v1 workspace state for authenticated user')
  } catch (error) {
    console.error('Failed to load v1 workspace state:', error)
  }
}

function handleAuthClose() {
  // If user tries to close auth modal without authenticating,
  // we could show a message or just keep it open
  console.debug('Auth modal closed without authentication')
}

onMounted(async () => {
  setupTauriListener()
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
    await authStore.checkAuth()
    if (authStore.isAuthenticated) {
      await handleAuthenticated(authStore.user)
    }
  } catch (error) {
    console.error('❌ Error during app initialization:', error)
  }
})

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
