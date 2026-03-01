<template>
  <header class="bg-gradient-to-r from-white to-gray-50 border-b border-pastel-500 px-4 sm:px-9 py-3 sm:py-4 shadow-sm">
    <div class="flex items-center justify-between">
      <!-- Left Section: Logo & Title -->
      <div class="flex items-center space-x-3 flex-shrink-0">
        <img :src="logo" alt="Inquira Logo" class="w-10 h-10 rounded-lg" />
        <div class="hidden sm:block">
          <h1 class="text-lg font-bold text-primary-900">Inquira</h1>
          <p class="text-xs text-primary-600">LLM-Powered Data Analysis</p>
        </div>
      </div>

      <!-- Center Section: Dataset Switcher (Prominent) -->
      <div class="flex-1 flex justify-center px-4 items-center space-x-3">
        <WorkspaceSwitcher />
        <DatasetSwitcher @open-settings="openSettings" />
      </div>

      <!-- Right Section: User Controls Group -->
      <div class="flex items-center space-x-3 flex-shrink-0">
        <div class="hidden lg:flex items-center space-x-2 px-2 py-1 rounded-md border border-gray-200 bg-white">
          <span
            v-if="kernelStatusMeta.showSpinner"
            class="inline-block w-3 h-3 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin"
            aria-hidden="true"
          ></span>
          <span class="text-xs font-medium" :class="kernelStatusMeta.textClass">
            Kernel: {{ kernelStatusMeta.label }}
          </span>
          <span
            v-if="appStore.runtimeError"
            class="max-w-[320px] truncate text-xs text-red-700"
            :title="appStore.runtimeError"
          >
            {{ appStore.runtimeError }}
          </span>
          <button
            @click="interruptKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning || kernelStatus === 'missing'"
            class="px-2 py-1 text-xs font-medium rounded border border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Interrupt current workspace kernel execution"
          >
            Interrupt
          </button>
          <button
            @click="restartKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning"
            class="px-2 py-1 text-xs font-medium rounded border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Restart workspace kernel and clear runtime state"
          >
            Restart
          </button>
        </div>

        <!-- Configuration Status Dot -->
        <div class="relative group">
          <div
            class="w-3 h-3 rounded-full cursor-help transition-all duration-200 hover:scale-110"
            :class="getStatusDotClasses"
            title="Click to open Settings"
            @click="openSettings()"
          ></div>

          <!-- Hover Tooltip -->
          <div class="absolute top-full mt-2 right-0 w-80 bg-white rounded-lg shadow-lg border border-pastel-300 p-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <div class="text-sm font-semibold text-primary-900 mb-3">Configuration Status</div>
            <div class="grid grid-cols-2 gap-3 max-w-md">
              <!-- Data File Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.hasDataFile ? 'border-success/20 bg-success/10' : 'border-gray-200 bg-gray-50'">
                <div class="w-2 h-2 rounded-full" :class="appStore.hasDataFile ? 'bg-success' : 'bg-gray-400'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.hasDataFile ? 'text-primary' : 'text-gray-600'">Data File</p>
                  <p class="text-xs" :class="appStore.hasDataFile ? 'text-primary' : 'text-gray-500'">{{ appStore.hasDataFile ? 'Set' : 'Optional' }}</p>
                </div>
              </div>

              <!-- Schema File Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.hasSchemaFile ? 'border-success/20 bg-success/10' : 'border-gray-200 bg-gray-50'">
                <div class="w-2 h-2 rounded-full" :class="appStore.hasSchemaFile ? 'bg-success' : 'bg-gray-400'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.hasSchemaFile ? 'text-primary' : 'text-gray-600'">Schema File</p>
                  <p class="text-xs" :class="appStore.hasSchemaFile ? 'text-primary' : 'text-gray-500'">{{ appStore.hasSchemaFile ? 'Set' : 'Optional' }}</p>
                </div>
              </div>

              <!-- Schema Context Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.schemaContext ? 'border-accent/20 bg-accent/10' : 'border-gray-200 bg-gray-50'">
                <div class="w-2 h-2 rounded-full" :class="appStore.schemaContext ? 'bg-accent' : 'bg-gray-400'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.schemaContext ? 'text-primary' : 'text-gray-600'">Schema Context</p>
                  <p class="text-xs" :class="appStore.schemaContext ? 'text-primary' : 'text-gray-500'">{{ appStore.schemaContext ? 'Set' : 'Optional' }}</p>
                </div>
              </div>

              <!-- API Key Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="appStore.apiKeyConfigured ? 'border-success/20 bg-success/10' : 'border-error/20 bg-error/10'">
                <div class="w-2 h-2 rounded-full" :class="appStore.apiKeyConfigured ? 'bg-success' : 'bg-error'"></div>
                <div>
                  <p class="text-xs font-medium" :class="appStore.apiKeyConfigured ? 'text-primary' : 'text-error'">API Key</p>
                  <p class="text-xs" :class="appStore.apiKeyConfigured ? 'text-primary' : 'text-error'">{{ appStore.apiKeyConfigured ? 'Configured' : 'Required' }}</p>
                </div>
              </div>

              <!-- WebSocket Connection Status -->
              <div class="flex items-center space-x-2 p-2 rounded border" :class="isWebSocketConnected ? 'border-success/20 bg-success/10' : 'border-error/20 bg-error/10'">
                <div class="w-2 h-2 rounded-full" :class="isWebSocketConnected ? 'bg-success' : 'bg-error'"></div>
                <div>
                  <p class="text-xs font-medium" :class="isWebSocketConnected ? 'text-primary' : 'text-error'">Backend Connection</p>
                  <p class="text-xs" :class="isWebSocketConnected ? 'text-primary' : 'text-error'">{{ isWebSocketConnected ? 'Connected' : 'Disconnected' }}</p>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-3 border-t border-pastel-300">
              <p class="text-xs text-primary-600 text-center">Click to open Settings</p>
            </div>
          </div>
        </div>

        <!-- Preview Actions removed; use Preview tab -->

        <!-- User Menu Dropdown -->
        <div class="relative" v-if="authStore.isAuthenticated">
          <button
            @click="toggleUserMenu"
            class="user-menu-button flex items-center space-x-2 px-4 py-3 text-sm font-medium text-primary bg-gray-50 hover:bg-gray-100 rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-sm"
            :class="{ 'bg-gray-100 shadow-md': isUserMenuOpen }"
            :title="`Logged in as ${authStore.username}`"
          >
            <div class="w-7 h-7 bg-gradient-to-br from-primary-600 to-accent-500 rounded-full flex items-center justify-center">
              <UserIcon class="h-3.5 w-3.5 text-white" />
            </div>
            <div class="hidden md:block text-left">
              <p class="text-sm font-semibold text-primary">{{ authStore.username }}</p>
              <p class="text-xs text-gray-500">{{ authStore.planLabel }} plan</p>
            </div>
            <ChevronDownIcon class="h-3.5 w-3.5 text-gray-400" />
          </button>

          <!-- Dropdown Menu -->
          <div
            v-if="isUserMenuOpen"
            class="user-menu-dropdown absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-50 border border-pastel-200"
            @click.stop
          >
            <!-- User Info Header -->
            <div class="px-4 py-3 border-b border-pastel-300 bg-pastel-500 rounded-t-lg">
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 bg-gradient-to-br from-primary-700 to-accent-600 rounded-full flex items-center justify-center">
                  <UserIcon class="h-4 w-4 text-white" />
                </div>
                <div>
                  <p class="text-sm font-semibold text-white">{{ authStore.username }}</p>
                  <p class="text-xs text-pastel-100">{{ authStore.planLabel }} plan</p>
                </div>
              </div>
            </div>

            <div class="py-1">
              <button
                @click="openSettings()"
                class="flex items-center w-full px-4 py-2.5 text-sm text-primary hover:bg-gray-50 hover:text-primary transition-colors"
              >
                <CogIcon class="h-4 w-4 mr-3 text-gray-500" />
                Settings
              </button>

              <button
                @click="openTerms"
                class="flex items-center w-full px-4 py-2.5 text-sm text-primary hover:bg-gray-50 hover:text-primary transition-colors"
              >
                <DocumentTextIcon class="h-4 w-4 mr-3 text-gray-500" />
                Terms &amp; Conditions
              </button>

              <div class="border-t border-pastel-200 my-1"></div>

              <button
                @click="handleLogout"
                class="flex items-center w-full px-4 py-2.5 text-sm text-error hover:bg-error/10 hover:text-error transition-colors"
              >
                <ArrowRightOnRectangleIcon class="h-4 w-4 mr-3" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>


  <!-- Settings Modal -->
  <SettingsModal
    :is-open="isSettingsOpen"
    :initial-tab="settingsInitialTab"
    @close="closeSettings"
  />

  <!-- Logout Confirmation Modal -->
  <ConfirmationModal
    :is-open="isLogoutConfirmOpen"
    title="Confirm Logout"
    :message="`Are you sure you want to log out, ${authStore.username}?`"
    confirm-text="Log Out"
    cancel-text="Cancel"
    @close="cancelLogout"
    @confirm="confirmLogout"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { settingsWebSocket } from '../../services/websocketService'
import { apiService } from '../../services/apiService'
import { toast } from '../../composables/useToast'
import SettingsModal from '../modals/SettingsModal.vue'
// PreviewModal removed; use in-panel tabs instead
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import { CogIcon, ArrowRightOnRectangleIcon, UserIcon, ChevronDownIcon, DocumentTextIcon } from '@heroicons/vue/24/outline'
import logo from '../../assets/favicon.svg'
import DatasetSwitcher from '../DatasetSwitcher.vue'
import WorkspaceSwitcher from '../WorkspaceSwitcher.vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api') // 'api' | 'data' | 'account'
// const isNewPreviewOpen = ref(false) // removed
const isUserMenuOpen = ref(false)
const isLogoutConfirmOpen = ref(false)
const isWebSocketConnected = ref(false)
const kernelStatus = ref('connecting')
const isKernelActionRunning = ref(false)
const isKernelStatusRequestInFlight = ref(false)
let kernelStatusPoller = null

// Computed property to check if configuration is complete
const isConfigurationComplete = computed(() => {
  return appStore.apiKeyConfigured && appStore.hasDataFile && isWebSocketConnected.value
})

// Computed property for status dot classes with blinking animation
const getStatusDotClasses = computed(() => {
  if (isConfigurationComplete.value) {
    return 'bg-success shadow-success/20 shadow-sm'
  } else {
    // Check if WebSocket is the issue
    if (!isWebSocketConnected.value) {
      return 'bg-error shadow-error/20 shadow-sm animate-pulse'
    } else {
      return 'bg-gray-400 shadow-gray-200 shadow-sm'
    }
  }
})

const kernelStatusMeta = computed(() => {
  if (appStore.runtimeError && appStore.activeWorkspaceId) {
    return { label: 'Error', textClass: 'text-red-700', showSpinner: false }
  }
  switch (String(kernelStatus.value || '').toLowerCase()) {
    case 'ready':
      return { label: 'Ready', textClass: 'text-green-700', showSpinner: false }
    case 'busy':
      return { label: 'Busy', textClass: 'text-amber-700', showSpinner: false }
    case 'starting':
    case 'connecting':
      return { label: 'Connecting', textClass: 'text-blue-700', showSpinner: true }
    case 'error':
      return { label: 'Error', textClass: 'text-red-700', showSpinner: false }
    case 'missing':
      if (appStore.activeWorkspaceId) {
        return { label: 'Missing', textClass: 'text-amber-700', showSpinner: false }
      }
      return { label: 'No Workspace', textClass: 'text-gray-600', showSpinner: false }
    default:
      return { label: appStore.activeWorkspaceId ? 'Connecting' : 'No Workspace', textClass: appStore.activeWorkspaceId ? 'text-blue-700' : 'text-gray-600', showSpinner: Boolean(appStore.activeWorkspaceId) }
  }
})

// Setup WebSocket connection monitoring
function setupWebSocketMonitoring() {
  // Monitor connection status
  const unsubscribe = settingsWebSocket.onConnection((connected) => {
    isWebSocketConnected.value = connected
    console.debug('WebSocket connection status changed:', connected)
  })

  // Set initial status
  isWebSocketConnected.value = settingsWebSocket.isConnected

  // Cleanup subscription when component unmounts
  onUnmounted(() => {
    if (typeof unsubscribe === 'function') unsubscribe()
  })
}

// Call auto-show when component is mounted
onMounted(() => {
  setupWebSocketMonitoring()
  startKernelStatusPolling()
})

onUnmounted(() => {
  stopKernelStatusPolling()
})

watch(
  () => appStore.activeWorkspaceId,
  async () => {
    await refreshKernelStatus()
  },
)

async function refreshKernelStatus() {
  if (!appStore.activeWorkspaceId) {
    kernelStatus.value = 'missing'
    return
  }
  if (isKernelStatusRequestInFlight.value) {
    return
  }
  isKernelStatusRequestInFlight.value = true
  try {
    const status = await apiService.v1GetWorkspaceKernelStatus(appStore.activeWorkspaceId)
    kernelStatus.value = String(status?.status || 'missing').toLowerCase()
    if (kernelStatus.value === 'ready' || kernelStatus.value === 'busy' || kernelStatus.value === 'starting') {
      appStore.setRuntimeError('')
    }
  } catch (error) {
    console.error('Failed to fetch kernel status:', error)
    kernelStatus.value = 'error'
    const message = error?.response?.data?.detail || error?.message || 'Failed to fetch kernel status.'
    appStore.setRuntimeError(message)
  } finally {
    isKernelStatusRequestInFlight.value = false
  }
}

function startKernelStatusPolling() {
  stopKernelStatusPolling()
  refreshKernelStatus()
  kernelStatusPoller = setInterval(() => {
    if (document.hidden) return
    refreshKernelStatus()
  }, 5000)
}

function stopKernelStatusPolling() {
  if (kernelStatusPoller) {
    clearInterval(kernelStatusPoller)
    kernelStatusPoller = null
  }
}

async function interruptKernel() {
  if (!appStore.activeWorkspaceId || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  try {
    const response = await apiService.v1InterruptWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) {
      toast.success('Kernel Interrupted', 'Execution interrupt signal sent.')
    } else {
      toast.error('Interrupt Failed', 'No running kernel found for this workspace.')
    }
    await refreshKernelStatus()
  } catch (error) {
    const message = error?.response?.data?.detail || error.message || 'Failed to interrupt kernel.'
    toast.error('Interrupt Failed', message)
  } finally {
    isKernelActionRunning.value = false
  }
}

async function restartKernel() {
  if (!appStore.activeWorkspaceId || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  kernelStatus.value = 'connecting'
  try {
    const response = await apiService.v1RestartWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) {
      appStore.setCodeRunning(false)
      toast.success('Kernel Restarted', 'Workspace kernel has been restarted.')
    } else {
      toast.error('Restart Failed', 'No kernel session existed for this workspace.')
    }
    await refreshKernelStatus()
  } catch (error) {
    const message = error?.response?.data?.detail || error.message || 'Failed to restart kernel.'
    toast.error('Restart Failed', message)
    await refreshKernelStatus()
  } finally {
    isKernelActionRunning.value = false
  }
}

function openSettings(tab = 'api') {
  const normalizedTab = typeof tab === 'string' ? tab.toLowerCase() : 'api'
  settingsInitialTab.value = ['api', 'data', 'account'].includes(normalizedTab) ? normalizedTab : 'api'
  isSettingsOpen.value = true
  isUserMenuOpen.value = false // Close dropdown when opening settings
}

function closeSettings() {
  isSettingsOpen.value = false
  settingsInitialTab.value = 'api' // Reset to default
}


// openNewPreview/closeNewPreview removed

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

function openTerms() {
  isUserMenuOpen.value = false
  window.open('/terms-and-conditions.html', '_blank', 'noopener')
}


function handleLogout() {
  // Show custom confirmation modal
  isLogoutConfirmOpen.value = true
  isUserMenuOpen.value = false // Close dropdown when opening logout confirmation
}

async function confirmLogout() {
  isLogoutConfirmOpen.value = false

  try {
    await authStore.logout()
    // The auth store will handle clearing the authentication state
    // and the UI will update automatically due to reactivity
  } catch (error) {
    console.error('Logout failed:', error)
  }
}

function cancelLogout() {
  isLogoutConfirmOpen.value = false
}

function handleKeydown(event) {

  // Don't handle Enter key - let it go to editors
  if (event.key === 'Enter') {
    return
  }

  // Caps Lock handling removed - now using Ctrl+Shift combinations

  // Handle Escape key to exit input fields and close modals/dropdowns
  if (event.key === 'Escape') {
    console.debug('Escape pressed')

    // Escape key handling for modal/dropdown closing

    // Close modals in priority order (most recent first)
    if (isLogoutConfirmOpen.value) {
      console.debug('Closing logout confirmation modal')
      cancelLogout()
      event.preventDefault()
      return
    }

    if (isSettingsOpen.value) {
      console.debug('Closing settings modal')
      closeSettings()
      event.preventDefault()
      return
    }

    // Close dropdowns
    if (isUserMenuOpen.value) {
      isUserMenuOpen.value = false
      event.preventDefault()
      return
    }

    // Exit input fields
    const activeElement = document.activeElement
    if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA' || activeElement.contentEditable === 'true')) {
      activeElement.blur()
      event.preventDefault()
      return
    }
  }

}



// Event listeners setup

// Add keyboard event listener
document.addEventListener('keydown', handleKeydown)

// Close user menu when clicking outside
document.addEventListener('click', (event) => {
  const userMenu = document.querySelector('.user-menu-dropdown')
  const userButton = document.querySelector('.user-menu-button')

  if (isUserMenuOpen.value && userMenu && userButton &&
      !userMenu.contains(event.target) && !userButton.contains(event.target)) {
    isUserMenuOpen.value = false
  }
})
</script>

<style scoped>
/* Custom urgent blinking animation for connection issues */
@keyframes urgentBlink {
  0%, 50% {
    opacity: 1;
    transform: scale(1);
  }
  25%, 75% {
    opacity: 0.3;
    transform: scale(0.95);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-pulse {
  animation: urgentBlink 1.5s ease-in-out infinite;
}

/* Ensure the tooltip appears above other elements */
.group:hover .absolute {
  z-index: 9999;
}
</style>
