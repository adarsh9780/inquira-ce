<template>
  <div
    class="flex flex-col border-r border-gray-200 bg-gray-50 transition-all duration-300 h-full shrink-0 z-40 shadow-sm relative overflow-visible"
    :class="appStore.isSidebarCollapsed ? 'w-16' : 'w-64'"
  >
    <!-- Top Section: Brand & Header -->
    <div 
      class="h-16 flex items-center px-3 border-b border-gray-200 shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
      @click="toggleSidebar"
      title="Toggle Sidebar"
    >
      <div class="flex items-center justify-center w-full">
        <div class="flex items-center min-w-0" :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start w-full'">
          <img :src="logo" alt="Inquira Logo" class="w-8 h-8 rounded shrink-0 shadow-sm" />
          <div v-show="!appStore.isSidebarCollapsed" class="ml-3 truncate">
            <h1 class="text-sm font-bold text-gray-800 tracking-tight leading-none">Inquira</h1>
            <p class="text-[10px] text-gray-500 font-medium mt-0.5">LLM-Powered Analysis</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Scrollable Middle Section -->
    <!-- Add padding right to avoid scrollbar overlapping content-->
    <div class="flex-1 overflow-y-auto overflow-x-hidden flex flex-col py-3 custom-scrollbar">
      
      <!-- File Explorer Sections -->
      <div class="flex flex-col space-y-2 mt-2">
        <SidebarWorkspaces 
          :is-collapsed="appStore.isSidebarCollapsed"
          @header-click="handleExplorerHeaderClick"
          @select="handleWorkspaceSelect"
        />
        <SidebarDatasets 
          :is-collapsed="appStore.isSidebarCollapsed"
          @header-click="handleExplorerHeaderClick"
          @select="handleDatasetSelect"
          @open-settings="openSettings"
        />
        <SidebarConversations 
          :is-collapsed="appStore.isSidebarCollapsed"
          @header-click="handleExplorerHeaderClick"
          @select="handleConversationSelect"
        />
      </div>

    </div>

    <!-- Bottom Section: Schema Link & User Menu -->
    <div class="border-t border-gray-200 bg-gray-100/50 p-2 shrink-0 flex flex-col gap-2">
      <!-- Schema Editor Link -->
      <button
        @click="handleTabClick('schema-editor')"
        class="w-full flex items-center justify-between p-2 rounded-lg transition-colors border"
        :class="appStore.activeTab === 'schema-editor' ? 'bg-white border-gray-200 shadow-sm text-blue-600' : 'border-transparent text-gray-600 hover:bg-gray-200/50'"
        title="Schema Editor"
      >
        <div class="flex items-center gap-2 min-w-0" :class="appStore.isSidebarCollapsed ? 'justify-center w-full' : ''">
          <DocumentTextIcon class="w-4 h-4 shrink-0 transition-transform" :class="appStore.activeTab === 'schema-editor' ? 'scale-110' : ''" />
          <span v-show="!appStore.isSidebarCollapsed" class="text-xs font-medium truncate" :class="appStore.activeTab === 'schema-editor' ? 'font-semibold' : ''">Schema Editor</span>
        </div>
      </button>
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
import { settingsWebSocket } from '../../services/websocketService'
import SettingsModal from '../modals/SettingsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import SidebarWorkspaces from './sidebar/SidebarWorkspaces.vue'
import SidebarDatasets from './sidebar/SidebarDatasets.vue'
import SidebarConversations from './sidebar/SidebarConversations.vue'
import logo from '../../assets/favicon.svg'

import {
  RectangleGroupIcon,
  CircleStackIcon,
  DocumentTextIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  ChevronUpIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

// State from RightPanel for notification counts
const flash = ref({})
const counts = computed(() => ({
  workspace: appStore.chatHistory?.length || (!appStore.isCodeRunning && appStore.generatedCode ? 1 : 0),
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

// Toolbar & User State
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api')
const isUserMenuOpen = ref(false)
const isLogoutConfirmOpen = ref(false)
const isWebSocketConnected = ref(false)

function handleTabClick(tabId) {
  appStore.setActiveTab(tabId)
}

function toggleSidebar() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function handleExplorerHeaderClick() {
  // Toggle off if expanded, expand if collapsed
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function handleWorkspaceSelect() {
  appStore.setActiveTab('workspace')
  appStore.setSidebarCollapsed(true)
}

function handleDatasetSelect() {
  appStore.setActiveTab('workspace')
  appStore.setSidebarCollapsed(true)
}

function handleConversationSelect() {
  appStore.setActiveTab('workspace')
  // We intentionally do NOT setSidebarCollapsed(true) here!
}

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
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', handleClickOutside)
})

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

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0; 
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: #cbd5e1;
}
</style>
