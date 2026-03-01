<template>
  <div
    class="flex flex-col border-r border-gray-200 bg-gray-50 transition-all duration-300 h-full shrink-0 z-40 shadow-sm relative"
    :class="[
      appStore.isSidebarCollapsed ? 'w-16' : 'w-64',
      isUserMenuOpen ? 'overflow-visible' : 'overflow-hidden'
    ]"
  >
    <!-- Top Section: Brand & Header -->
    <div class="h-16 flex items-center px-4 border-b border-gray-200 shrink-0">
      <div class="flex items-center">
        <!-- Logo always visible -->
        <img :src="logo" alt="Inquira Logo" class="w-8 h-8 rounded shrink-0 shadow-sm cursor-pointer hover:opacity-80 transition-opacity" @click="appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)" title="Toggle Sidebar" />
        <!-- Brand Name (Hidden when collapsed) -->
        <div v-show="!appStore.isSidebarCollapsed" class="ml-3 truncate">
          <h1 class="text-sm font-bold text-gray-800 tracking-tight leading-none">Inquira</h1>
          <p class="text-[10px] text-gray-500 font-medium mt-0.5">LLM-Powered Analysis</p>
        </div>
      </div>
    </div>

    <!-- Scrollable Middle Section -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden flex flex-col py-3">
      
      <!-- Workspace & Dataset Switcher (Hidden when collapsed) -->
      <div v-show="!appStore.isSidebarCollapsed" class="px-4 mb-6 space-y-3">
        <div>
          <label class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block px-1">Workspace</label>
          <WorkspaceSwitcher />
        </div>
        <div>
          <label class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block px-1">Data Source</label>
          <DatasetSwitcher @open-settings="openSettings" />
        </div>
      </div>

      <!-- Views / Tabs Navigation -->
      <div class="px-2">
        <div v-show="!appStore.isSidebarCollapsed" class="mb-2 px-3 flex items-center justify-between">
          <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Views</span>
        </div>
        
        <nav class="flex flex-col space-y-1.5" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="handleTabClick(tab.id)"
            :class="[
              (tab.id === 'terminal' ? appStore.isTerminalOpen : appStore.activeTab === tab.id)
                ? 'bg-white text-blue-600 shadow-sm border border-gray-200/60 ring-1 ring-black/5'
                : 'text-gray-600 hover:bg-gray-200/50 hover:text-gray-900 border border-transparent',
              'relative w-full rounded-lg font-medium text-sm transition-all duration-200 flex items-center',
              appStore.isSidebarCollapsed ? 'p-2.5 justify-center mx-auto aspect-square max-w-[40px]' : 'py-2 px-3 justify-start',
              flash[tab.id] ? 'ring-2 ring-green-400 ring-offset-1 animate-pulse' : ''
            ]"
            :title="tab.name"
          >
            <!-- Highlight indicator line -->
            <div v-if="(tab.id === 'terminal' ? appStore.isTerminalOpen : appStore.activeTab === tab.id)" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-1/2 bg-blue-600 rounded-r-full"></div>

            <div class="relative flex w-full items-center" :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start ml-1.5'">
              <component :is="tab.icon" class="h-4 w-4 shrink-0 transition-transform" :class="(tab.id === 'terminal' ? appStore.isTerminalOpen : appStore.activeTab === tab.id) ? 'scale-110' : ''" />
              <span v-show="!appStore.isSidebarCollapsed" class="ml-2.5 truncate" :class="(tab.id === 'terminal' ? appStore.isTerminalOpen : appStore.activeTab === tab.id) ? 'font-semibold' : ''">{{ tab.name }}</span>

              <span v-if="appStore.isSidebarCollapsed && tab.count && Number(tab.count) > 0"
                    class="absolute -right-1 -top-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[9px] font-bold text-white shadow-sm ring-2 ring-gray-50"
                    :class="tab.badgeColor">
                {{ tab.count }}
              </span>
              <span v-else-if="!appStore.isSidebarCollapsed && tab.count && Number(tab.count) > 0"
                    class="ml-auto inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold shadow-sm"
                    :class="tab.badgeClass">
                {{ tab.count }}
              </span>
            </div>
          </button>
        </nav>
      </div>

    </div>

    <!-- Bottom Section: User & Status -->
    <div class="border-t border-gray-200 bg-gray-100/50 p-3 shrink-0">
      
      <!-- Status Badges (Hidden when collapsed) -->
      <div v-show="!appStore.isSidebarCollapsed" class="mb-3 space-y-2">
        <!-- Kernel Status -->
        <div class="flex items-center justify-between text-xs px-2 py-1.5 bg-white border border-gray-200 rounded-md shadow-sm">
          <div class="flex items-center gap-1.5 truncate">
            <span
              v-if="kernelStatusMeta.showSpinner"
              class="inline-block w-2.5 h-2.5 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin shrink-0"
              aria-hidden="true"
            ></span>
            <span v-else class="w-2.5 h-2.5 rounded-full shrink-0" :class="kernelStatusMeta.dotClass"></span>
            <span class="font-medium truncate" :class="kernelStatusMeta.textClass">
              {{ kernelStatusMeta.label }}
            </span>
          </div>
          
          <div class="flex ml-1 gap-1 shrink-0">
            <button
              @click="interruptKernel"
              :disabled="!appStore.activeWorkspaceId || isKernelActionRunning || kernelStatus === 'missing'"
              class="p-1 rounded text-gray-400 hover:bg-gray-100 hover:text-amber-600 disabled:opacity-30 disabled:hover:bg-transparent"
              title="Interrupt Kernel"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path d="M5.25 3A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17h9.5A2.25 2.25 0 0017 14.75v-9.5A2.25 2.25 0 0014.75 3h-9.5zM6 6.75a.75.75 0 01.75-.75h6.5a.75.75 0 01.75.75v6.5a.75.75 0 01-.75.75h-6.5a.75.75 0 01-.75-.75v-6.5z" /></svg>
            </button>
            <button
              @click="restartKernel"
              :disabled="!appStore.activeWorkspaceId || isKernelActionRunning"
              class="p-1 rounded text-gray-400 hover:bg-gray-100 hover:text-red-500 disabled:opacity-30 disabled:hover:bg-transparent"
              title="Restart Kernel"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" /></svg>
            </button>
          </div>
        </div>

        <div v-if="appStore.runtimeError" class="text-[10px] text-red-600 px-1 truncate" :title="appStore.runtimeError">
          {{ appStore.runtimeError }}
        </div>
      </div>

      <!-- User Menu Toggle -->
      <div class="relative w-full" v-if="authStore.isAuthenticated">
        <button
          @click="toggleUserMenu"
          class="w-full flex items-center justify-between p-1.5 rounded-lg hover:bg-white border border-transparent hover:border-gray-200 transition-colors"
          title="Account & Settings"
        >
          <div class="flex items-center gap-2 min-w-0">
            <div class="relative shrink-0">
              <div class="w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center shadow-sm text-white font-medium text-xs">
                {{ authStore.username ? authStore.username.charAt(0).toUpperCase() : 'U' }}
              </div>
              <!-- Status Dot Overlay on Avatar -->
              <div
                class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-gray-100"
                :class="getStatusDotClasses"
              ></div>
            </div>
            
            <div v-show="!appStore.isSidebarCollapsed" class="flex-1 text-left truncate">
              <p class="text-xs font-semibold text-gray-800 truncate">{{ authStore.username }}</p>
              <p class="text-[10px] text-gray-500 truncate">{{ authStore.planLabel }}</p>
            </div>
          </div>
          <ChevronUpIcon v-show="!appStore.isSidebarCollapsed" class="h-3.5 w-3.5 text-gray-400 shrink-0" />
        </button>

        <!-- Dropdown Menu (Renders above the button) -->
        <div
          v-if="isUserMenuOpen"
          class="absolute bottom-full left-0 mb-2 w-56 bg-white rounded-lg shadow-xl ring-1 ring-black/5 z-50 border border-gray-100 overflow-hidden text-left"
          @click.stop
        >
          <!-- User Info Header -->
          <div class="px-3 py-2.5 border-b border-gray-100 bg-gray-50/50">
            <p class="text-sm font-semibold text-gray-800">{{ authStore.username }}</p>
            <p class="text-[10px] bg-blue-100 text-blue-700 font-medium px-1.5 py-0.5 rounded w-max mt-0.5">{{ authStore.planLabel }}</p>
          </div>

          <!-- Configuration Status Overview -->
          <div class="px-3 py-2 border-b border-gray-100 text-[10px]" @click="openSettings('api')">
            <div class="flex items-center justify-between mb-1 hover:bg-gray-50 cursor-pointer p-1 rounded">
              <span class="text-gray-600">WS Connection</span>
              <span class="w-2 h-2 rounded-full" :class="isWebSocketConnected ? 'bg-green-500' : 'bg-red-500'"></span>
            </div>
            <div class="flex items-center justify-between mb-1 hover:bg-gray-50 cursor-pointer p-1 rounded">
              <span class="text-gray-600">API Key Config</span>
              <span class="w-2 h-2 rounded-full" :class="appStore.apiKeyConfigured ? 'bg-green-500' : 'bg-red-500'"></span>
            </div>
          </div>

          <div class="py-1">
            <button
              @click="openSettings('api')"
              class="flex items-center w-full px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <CogIcon class="h-4 w-4 mr-2.5 text-gray-400" />
              Settings
            </button>

            <button
              @click="openTerms"
              class="flex items-center w-full px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <DocumentTextIcon class="h-4 w-4 mr-2.5 text-gray-400" />
              Terms &amp; Conditions
            </button>

            <div class="border-t border-gray-100 my-1"></div>

            <button
              @click="handleLogout"
              class="flex items-center w-full px-4 py-2 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              <ArrowRightOnRectangleIcon class="h-4 w-4 mr-2.5" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <SettingsModal
      :is-open="isSettingsOpen"
      :initial-tab="settingsInitialTab"
      @close="closeSettings"
    />

    <ConfirmationModal
      :is-open="isLogoutConfirmOpen"
      title="Confirm Logout"
      :message="`Are you sure you want to log out, ${authStore.username}?`"
      confirm-text="Log Out"
      cancel-text="Cancel"
      @close="cancelLogout"
      @confirm="confirmLogout"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { apiService } from '../../services/apiService'
import { settingsWebSocket } from '../../services/websocketService'
import { toast } from '../../composables/useToast'
import SettingsModal from '../modals/SettingsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import DatasetSwitcher from '../DatasetSwitcher.vue'
import WorkspaceSwitcher from '../WorkspaceSwitcher.vue'
import logo from '../../assets/favicon.svg'

import {
  RectangleGroupIcon,
  TableCellsIcon,
  ChartBarIcon,
  CommandLineIcon,
  CircleStackIcon,
  DocumentTextIcon,
  EyeIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  UserIcon,
  ChevronUpIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

// State from RightPanel
const flash = ref({})
const counts = computed(() => ({
  workspace: appStore.chatHistory?.length || (!appStore.isCodeRunning && appStore.generatedCode ? 1 : 0),
  terminal: appStore.terminalOutput && !appStore.isCodeRunning ? 1 : 0,
}))

watch(counts, (n, o) => {
  if (!o) return
  for (const k of Object.keys(n)) {
    if ((n[k] || 0) > (o[k] || 0)) {
      flash.value = { ...flash.value, [k]: true }
      setTimeout(() => {
        flash.value = { ...flash.value, [k]: false }
      }, 1000)
    }
  }
}, { deep: true })

const tabs = computed(() => [
  {
    id: 'workspace',
    name: 'Workspace',
    icon: RectangleGroupIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-blue-600',
  },
  ...(appStore.terminalEnabled ? [{
    id: 'terminal',
    name: 'Terminal',
    icon: CommandLineIcon,
    count: appStore.terminalOutput && !appStore.isCodeRunning ? '1' : null,
    badgeClass: appStore.terminalOutput && !appStore.isCodeRunning ? 'bg-gray-100 text-gray-800' : '',
    badgeColor: 'bg-slate-700',
  }] : []),
  {
    id: 'preview',
    name: 'Preview',
    icon: EyeIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-gray-400',
  },
  {
    id: 'schema-editor',
    name: 'Schema',
    icon: DocumentTextIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-gray-400',
  },
])

// State from TopToolbar
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api')
const isUserMenuOpen = ref(false)
const isLogoutConfirmOpen = ref(false)
const isWebSocketConnected = ref(false)
const kernelStatus = ref('connecting')
const isKernelActionRunning = ref(false)
const isKernelStatusRequestInFlight = ref(false)
let kernelStatusPoller = null

const isConfigurationComplete = computed(() => {
  return appStore.apiKeyConfigured && appStore.hasDataFile && isWebSocketConnected.value
})

function handleTabClick(tabId) {
  if (tabId === 'terminal') {
    appStore.toggleTerminal()
  } else {
    appStore.setActiveTab(tabId)
    // Optional: Hide terminal if switching to a non-workspace full screen view
    if (appStore.isTerminalOpen && ['preview', 'schema-editor'].includes(tabId)) {
      // Keep it conceptually "open" for when we return to workspace, or close it
      // we'll leave it as is, standard appStore logic handles visibility via v-show
    }
  }
}

const getStatusDotClasses = computed(() => {
  if (isConfigurationComplete.value) {
    return 'bg-green-500'
  } else {
    if (!isWebSocketConnected.value) {
      return 'bg-red-500 animate-pulse'
    } else {
      return 'bg-gray-400'
    }
  }
})

const kernelStatusMeta = computed(() => {
  if (appStore.runtimeError && appStore.activeWorkspaceId) {
    return { label: 'Error', textClass: 'text-red-700', dotClass: 'bg-red-500', showSpinner: false }
  }
  switch (String(kernelStatus.value || '').toLowerCase()) {
    case 'ready':
      return { label: 'Ready', textClass: 'text-green-700', dotClass: 'bg-green-500', showSpinner: false }
    case 'busy':
      return { label: 'Busy', textClass: 'text-amber-700', dotClass: 'bg-amber-500', showSpinner: false }
    case 'starting':
    case 'connecting':
      return { label: 'Connecting', textClass: 'text-blue-700', dotClass: 'bg-blue-500', showSpinner: true }
    case 'error':
      return { label: 'Error', textClass: 'text-red-700', dotClass: 'bg-red-500', showSpinner: false }
    case 'missing':
      if (appStore.activeWorkspaceId) {
        return { label: 'Missing', textClass: 'text-amber-700', dotClass: 'bg-amber-500', showSpinner: false }
      }
      return { label: 'No WS', textClass: 'text-gray-500', dotClass: 'bg-gray-300', showSpinner: false }
    default:
      return { label: appStore.activeWorkspaceId ? 'Connecting' : 'No WS', textClass: appStore.activeWorkspaceId ? 'text-blue-700' : 'text-gray-500', dotClass: appStore.activeWorkspaceId ? 'bg-blue-500' : 'bg-gray-300', showSpinner: Boolean(appStore.activeWorkspaceId) }
  }
})

// Lifecycle and Event Handling
function setupWebSocketMonitoring() {
  const unsubscribe = settingsWebSocket.onConnection((connected) => {
    isWebSocketConnected.value = connected
  })
  isWebSocketConnected.value = settingsWebSocket.isConnected
  onUnmounted(() => {
    if (typeof unsubscribe === 'function') unsubscribe()
  })
}

onMounted(() => {
  setupWebSocketMonitoring()
  startKernelStatusPolling()
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  stopKernelStatusPolling()
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', handleClickOutside)
})

watch(() => appStore.activeWorkspaceId, async () => {
    await refreshKernelStatus()
})

async function refreshKernelStatus() {
  if (!appStore.activeWorkspaceId) {
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
    kernelStatus.value = 'error'
    appStore.setRuntimeError(error?.response?.data?.detail || error?.message || 'Failed to fetch kernel status.')
  } finally {
    isKernelStatusRequestInFlight.value = false
  }
}

function startKernelStatusPolling() {
  stopKernelStatusPolling()
  refreshKernelStatus()
  kernelStatusPoller = setInterval(() => {
    if (!document.hidden) refreshKernelStatus()
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
  if (!appStore.activeWorkspaceId || isKernelActionRunning.value) return
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

function openSettings(tab = 'api') {
  settingsInitialTab.value = tab
  isSettingsOpen.value = true
  isUserMenuOpen.value = false
}

function closeSettings() {
  isSettingsOpen.value = false
  settingsInitialTab.value = 'api'
}

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

function openTerms() {
  isUserMenuOpen.value = false
  window.open('/terms-and-conditions.html', '_blank', 'noopener')
}

function handleLogout() {
  isLogoutConfirmOpen.value = true
  isUserMenuOpen.value = false
}

async function confirmLogout() {
  isLogoutConfirmOpen.value = false
  try { await authStore.logout() } catch (e) { console.error('Logout failed:', e) }
}

function cancelLogout() {
  isLogoutConfirmOpen.value = false
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    if (isLogoutConfirmOpen.value) return cancelLogout()
    if (isSettingsOpen.value) return closeSettings()
    if (isUserMenuOpen.value) return (isUserMenuOpen.value = false)
    
    const activeE = document.activeElement
    if (activeE && ['INPUT', 'TEXTAREA'].includes(activeE.tagName) || activeE.contentEditable === 'true') {
      activeE.blur()
    }
  }
}

function handleClickOutside(event) {
  if (isUserMenuOpen.value) {
    const el = event.target.closest('.relative.w-full')
    if (!el) isUserMenuOpen.value = false
  }
}
</script>

<style scoped>
@keyframes urgentBlink {
  0%, 50%, 100% { opacity: 1; transform: scale(1); }
  25%, 75% { opacity: 0.3; transform: scale(0.95); }
}
.animate-pulse {
  animation: urgentBlink 1.5s ease-in-out infinite;
}
/* Webkit Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>
