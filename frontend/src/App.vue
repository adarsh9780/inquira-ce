<template>
  <div class="min-h-screen bg-white flex flex-col">
    <!-- Toast Notifications -->
    <ToastContainer />

    <!-- Connection Status Indicator -->
    <ConnectionStatusIndicator />

    <!-- Authentication Modal -->
    <!-- Auth Modal -->
    <AuthModal
      :is-open="!authStore.isAuthenticated && !authStore.isLoading"
      @close="handleAuthClose"
      @authenticated="handleAuthenticated"
    />

    <!-- Main App (only shown when authenticated) -->
    <div v-if="authStore.isAuthenticated" class="flex flex-col h-screen">
      <!-- Main Content Area with Sidebar -->
      <div class="flex-1 flex overflow-hidden bg-white">
        <!-- New Unified Left Sidebar -->
        <UnifiedSidebar />

        <!-- Single Panel - Tabs include Chat -->
        <div class="flex-1 bg-white flex flex-col overflow-hidden">
          <RightPanel />
        </div>
      </div>
      
      <!-- Footer Status Bar -->
      <StatusBar />
    </div>

    <!-- Loading Screen -->
    <div v-else-if="authStore.isLoading" class="flex items-center justify-center h-screen bg-gray-50">
      <div class="text-center">
        <div class="animate-spin rounded-full h-16 w-16 border-4 border-gray-300 border-t-primary mx-auto mb-6"></div>
        <h2 class="text-2xl font-semibold text-primary mb-2">Loading Inquira</h2>
        <p class="text-gray-600 text-lg">Preparing your data analysis workspace...</p>
      </div>
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
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useAppStore } from './stores/appStore'
import { useAuthStore } from './stores/authStore'
import { settingsWebSocket } from './services/websocketService'
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
  // Establish persistent WebSocket connection
  try {
    await settingsWebSocket.connectPersistent(userData.user_id)
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
      appStore.setRuntimeError(message || 'Workspace runtime bootstrap failed.')
      if (!workspaceRuntimeStatus.active) return
      workspaceRuntimeStatus.active = false
      workspaceRuntimeStatus.message = message || ''
    }),
  )
  try {
    await appStore.loadLocalConfig()
    await authStore.checkAuth()
    if (authStore.isAuthenticated) {
      await handleAuthenticated(authStore.user)
    }
  } catch (error) {
    console.error('❌ Error during app initialization:', error)
  }
})

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
/* Global styles for the application */
.monaco-editor {
  border-radius: 0.375rem;
}

.ag-theme-alpine {
  --ag-border-color: #a3a2cd;
  --ag-header-background-color: #d1d1e6;
  --ag-odd-row-background-color: #ffffff;
  --ag-even-row-background-color: #e8e8f3;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #d1d1e6;
}

::-webkit-scrollbar-thumb {
  background: #8a89c0;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #6160a9;
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
</style>
