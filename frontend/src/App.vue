<template>
  <div class="min-h-screen bg-white flex flex-col">
    <!-- Toast Notifications -->
    <ToastContainer />

    <!-- Connection Status Indicator -->
    <ConnectionStatusIndicator />

    <!-- Authentication Modal -->
    <AuthModal
      :is-open="!authStore.isAuthenticated && !authStore.isLoading"
      @close="handleAuthClose"
      @authenticated="handleAuthenticated"
    />

    <!-- Main App (only shown when authenticated) -->
    <div v-if="authStore.isAuthenticated" class="flex flex-col h-screen">
      <!-- Top Toolbar -->
      <TopToolbar />

      <!-- Main Content Area -->
      <div class="flex-1 flex overflow-hidden bg-white">
        <!-- Single Panel - Tabs include Chat -->
        <div class="flex-1 bg-white flex flex-col overflow-hidden">
          <RightPanel />
        </div>
      </div>
    </div>

    <!-- Loading Screen -->
    <div v-else-if="authStore.isLoading" class="flex items-center justify-center h-screen bg-gray-50">
      <div class="text-center">
        <div class="animate-spin rounded-full h-16 w-16 border-4 border-gray-300 border-t-primary mx-auto mb-6"></div>
        <h2 class="text-2xl font-semibold text-primary mb-2">Loading Inquira</h2>
        <p class="text-gray-600 text-lg">Preparing your data analysis workspace...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useAppStore } from './stores/appStore'
import { useAuthStore } from './stores/authStore'
import { apiService } from './services/apiService'
import { settingsWebSocket } from './services/websocketService'
import AuthModal from './components/modals/AuthModal.vue'
import TopToolbar from './components/layout/TopToolbar.vue'
import RightPanel from './components/layout/RightPanel.vue'
import ToastContainer from './components/ui/ToastContainer.vue'
import ConnectionStatusIndicator from './components/ui/ConnectionStatusIndicator.vue'

const appStore = useAppStore()
const authStore = useAuthStore()

async function handleAuthenticated(userData) {
  console.log('User authenticated:', userData)

  // Establish persistent WebSocket connection
  try {
    console.log('🔌 Establishing persistent WebSocket connection...')
    await settingsWebSocket.connectPersistent(userData.user_id)
    console.log('✅ Persistent WebSocket connection established')
  } catch (wsError) {
    console.error('❌ Failed to establish persistent WebSocket connection:', wsError)
    // Don't block authentication if WebSocket fails
  }

  // After successful authentication, check if user has settings
  try {
    const settings = await apiService.getSettings()
    console.log('User settings:', settings)

    // Update app store with user settings, but preserve local state
    // Check if backend indicates fresh/empty state but we have local settings
    const isBackendEmpty = !settings.api_key && !settings.data_path
    const hasLocalSettings = appStore.apiKey || appStore.dataFilePath

    if (isBackendEmpty && hasLocalSettings) {
      console.warn('⚠️ Backend reset detected. Attempting to reconcile state...')
      
      // 1. Try to restore API key if we have it locally
      if (appStore.apiKey) {
        try {
          console.log('🔄 Restoring local API key to fresh backend...')
          await apiService.setApiKey(appStore.apiKey)
          // Don't show toast for successful restore to keep it seamless, or maybe a subtle one
          const { toast } = await import('./composables/useToast')
          toast.success('Session Restored', 'Your API key was restored to the new database.')
        } catch (restoreError) {
          console.error('❌ Failed to restore API key:', restoreError)
        }
      }

      // 2. Clear data path/context regardless, as the file reference in DB is gone
      // and we want to force user to re-select to ensure schema generation triggers correctly
      if (appStore.dataFilePath) {
        console.warn('🧹 Clearing local data path to match fresh backend.')
        appStore.setDataFilePath('')
        appStore.setSchemaContext('')
        appStore.setIsSchemaFileUploaded(false)
        appStore.setSchemaFileId(null)
        
        const { toast } = await import('./composables/useToast')
        toast.info('Workspace Reset', 'Backend database was reset. Please re-select your dataset.')
      }

      // Continue to load other settings (which are empty/defaults now)
      // We don't return here because we want the rest of the flow (e.g. chat history fetch) to run
    }

    if (settings.api_key) {
      appStore.setApiKey(settings.api_key)
    } else {
      try {
        const apiKeyResponse = await apiService.getApiKey()
        if (apiKeyResponse?.api_key) {
          appStore.setApiKey(apiKeyResponse.api_key)
          console.log('🔑 API key rehydrated from dedicated endpoint')
        }
      } catch (apiKeyError) {
        console.error('❌ Failed to rehydrate API key from backend:', apiKeyError)
      }
    }
    if (settings.data_path) {
      appStore.setDataFilePath(settings.data_path)
    }
    if (settings.schema_path) {
      appStore.setSchemaFilePath(settings.schema_path)
    }

    // If schema exists on backend but localStorage doesn't know about it,
    // update the local state to reflect this
    if (settings.data_path && !appStore.isSchemaFileUploaded) {
      // Try to check if schema exists on backend
      try {
        await apiService.loadSchema(settings.data_path)
        appStore.setIsSchemaFileUploaded(true)
        console.log('Schema found on backend, updated local state')
      } catch (schemaError) {
        // Schema doesn't exist, that's fine
        console.log('No schema found on backend')
      }
    }

    // Force fetch chat history to ensure it's loaded
    if (settings.data_path) {
        console.log("🔄 Force fetching chat history from App.vue")
        appStore.fetchChatHistory()
    }

    console.log('Settings loaded for authenticated user')
  } catch (error) {
    console.log('No existing settings found for user (or new user checking in)')
    
    // Also check here for desync if getSettings throws 404 or similar
    // If we have local settings but backend says "no settings found", clear local
    if (appStore.apiKey || appStore.dataFilePath) {
      console.warn('⚠️ No backend settings found but local has data. Clearing local config.')
      appStore.clearLocalConfig()
      const { toast } = await import('./composables/useToast')
      toast.info('Settings Reset', 'Backend database was reset. Local settings have been cleared.')
    }
  }
}

function handleAuthClose() {
  // If user tries to close auth modal without authenticating,
  // we could show a message or just keep it open
  console.log('Auth modal closed without authentication')
}

onMounted(async () => {
  try {
    // Load local configuration first
    appStore.loadLocalConfig()

    // Check authentication status on app load
    await authStore.checkAuth()

    // If authenticated, load user settings and establish WebSocket
    if (authStore.isAuthenticated) {
      await handleAuthenticated(authStore.user)
    }
  } catch (error) {
    console.error('❌ Error during app initialization:', error)
    // Continue with app initialization even if there are errors
    // The auth modal will show if user is not authenticated
  }
})

// Cleanup on unmount
onUnmounted(() => {
  // Disconnect persistent WebSocket connection
  if (settingsWebSocket.isPersistentMode) {
    console.log('🧹 Cleaning up persistent WebSocket connection')
    settingsWebSocket.disconnectPersistent()
  }
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
</style>
