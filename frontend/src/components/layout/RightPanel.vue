<template>
  <div class="flex h-full bg-white overflow-hidden">
    <!-- Vertical Tab Navigation -->
    <div
      class="border-r border-gray-100 bg-gradient-to-b from-gray-50 to-slate-50 p-2 sm:p-3 transition-all duration-200"
      :class="appStore.isSidebarCollapsed ? 'w-16 sm:w-16 lg:w-16' : 'w-44 sm:w-52 lg:w-56'"
    >
      <div class="flex items-center justify-between mb-2">
        <span v-if="!appStore.isSidebarCollapsed" class="text-xs font-semibold text-gray-500 ml-1">Views</span>
        <button
          class="ml-auto rounded-md p-1.5 hover:bg-gray-200 text-gray-600"
          :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
            <path v-if="appStore.isSidebarCollapsed" fill-rule="evenodd" d="M3 12a1 1 0 011-1h11.586l-3.293-3.293a1 1 0 111.414-1.414l5 5a1 1 0 010 1.414l-5 5a1 1 0 11-1.414-1.414L15.586 13H4a1 1 0 01-1-1z" clip-rule="evenodd" />
            <path v-else fill-rule="evenodd" d="M21 12a1 1 0 01-1 1H8.414l3.293 3.293a1 1 0 11-1.414 1.414l-5-5a1 1 0 010-1.414l5-5a1 1 0 111.414 1.414L8.414 11H20a1 1 0 011 1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>

      <nav class="flex flex-col space-y-2" aria-label="Tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="handleTabClick(tab.id)"
          :class="[
            (appStore.activeTab === tab.id || (tab.id === 'chat' && appStore.isChatOverlayOpen))
              ? 'bg-white text-blue-600 shadow-lg border-blue-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-800 border-gray-200',
            'relative w-full border rounded-lg sm:rounded-xl font-semibold text-sm transition-all duration-200 flex items-center leading-none',
            appStore.isSidebarCollapsed ? 'h-12 aspect-square justify-center p-3' : 'py-3 px-3 justify-start',
            flash[tab.id] ? 'ring-2 ring-green-400 ring-offset-1 animate-pulse' : '',
            (appStore.isLoading && tab.id === 'code' && appStore.activeTab !== 'code')
              ? 'ring-2 ring-blue-300 ring-offset-1 animate-pulse'
              : ''
          ]"
          :title="`Press ${tab.shortcut.slice(-1)} to switch to ${tab.name} tab`"
        >
          <!-- Unified inner layout: same icon element both states -->
          <div class="relative flex items-center w-full" :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start'">
            <component :is="tab.icon" class="h-5 w-5 flex-shrink-0" />
            <span v-show="!appStore.isSidebarCollapsed" class="whitespace-nowrap text-sm font-medium ml-2">{{ tab.name }}</span>

            <!-- Loading spinner shown only when expanded on Code tab -->
            <div v-if="!appStore.isSidebarCollapsed && tab.id === 'code' && appStore.isLoading" class="ml-auto">
              <div class="animate-spin rounded-full h-3 w-3 border border-gray-300 border-t-blue-600"></div>
            </div>

            <!-- Badge placement differs by state -->
            <span v-if="appStore.isSidebarCollapsed && tab.count && Number(tab.count) > 0"
                  class="absolute top-1 right-1 inline-flex items-center justify-center text-white text-[10px] font-bold rounded-full h-5 min-w-[18px] px-1 shadow-md ring-2 ring-white"
                  :class="tab.badgeColor">
              {{ tab.count }}
            </span>
            <span v-else-if="!appStore.isSidebarCollapsed && tab.count && Number(tab.count) > 0"
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-bold shadow-sm ml-auto"
                  :class="tab.badgeClass">
              {{ tab.count }}
            </span>
          </div>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div class="relative flex-1 overflow-hidden bg-gray-50/50">
      <!-- Chat Overlay (Resizable) -->
      <div
        v-show="appStore.isChatOverlayOpen"
        class="absolute inset-y-0 left-0 bg-white border-r border-gray-200 shadow-xl z-20 flex flex-col"
        :style="{ width: `${Math.round(appStore.chatOverlayWidth * 100)}%` }"
      >
        <div class="h-full p-3 sm:p-4 overflow-hidden">
          <ChatTab />
        </div>
        
        <!-- Resize Handle -->
        <div
          class="absolute top-0 right-0 w-1.5 h-full cursor-ew-resize group z-30 flex items-center justify-center translate-x-1/2"
          @mousedown="startResize"
        >
          <!-- The handle itself -->
          <div class="h-12 w-1 rounded-full bg-gray-200 group-hover:bg-blue-400 group-active:bg-blue-600 transition-colors"></div>
          
          <!-- Large hit area -->
          <div class="absolute inset-y-0 -left-2 -right-2 bg-transparent group-hover:bg-blue-500/5 transition-all duration-150 rounded-lg"></div>
        </div>
      </div>

      <!-- Main content shifts when chat is open -->
      <div
        class="h-full transition-all duration-200"
        :style="appStore.isChatOverlayOpen ? { marginLeft: `${Math.round(appStore.chatOverlayWidth * 100)}%` } : {}"
      >
      <!-- Chat Tab -->
      <div v-show="false" class="h-full p-3 sm:p-4"></div>

      <!-- Code Tab -->
      <div v-show="appStore.activeTab === 'code'" class="h-full p-3 sm:p-4">
        <CodeTab />
      </div>

      <!-- Table Tab -->
      <div v-show="appStore.activeTab === 'table'" class="h-full p-3 sm:p-4">
        <TableTab />
      </div>

      <!-- Figure Tab -->
      <div v-show="appStore.activeTab === 'figure'" class="h-full p-3 sm:p-4">
        <FigureTab />
      </div>

      <!-- Terminal Tab -->
      <div v-show="appStore.activeTab === 'terminal'" class="h-full p-3 sm:p-4">
        <TerminalTab />
      </div>

      <!-- Preview Tab -->
      <div v-show="appStore.activeTab === 'preview'" class="h-full p-3 sm:p-4">
        <PreviewTab />
      </div>

      <!-- Schema Editor Tab -->
      <div v-show="appStore.activeTab === 'schema-editor'" class="h-full p-3 sm:p-4">
        <SchemaEditorTab />
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import CodeTab from '../analysis/CodeTab.vue'
import TableTab from '../analysis/TableTab.vue'
import FigureTab from '../analysis/FigureTab.vue'
import TerminalTab from '../analysis/TerminalTab.vue'
import { 
  CodeBracketIcon, 
  TableCellsIcon, 
  ChartBarIcon, 
  CommandLineIcon, 
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  EyeIcon
} from '@heroicons/vue/24/outline'
import ChatTab from '../chat/ChatTab.vue'
import PreviewTab from '../preview/PreviewTab.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'

const appStore = useAppStore()

const tabs = computed(() => [
  {
    id: 'chat',
    name: 'Chat',
    icon: ChatBubbleLeftRightIcon,
    count: (appStore.chatHistory && appStore.chatHistory.length > 0) ? String(appStore.chatHistory.length) : null,
    badgeClass: (appStore.chatHistory && appStore.chatHistory.length > 0) ? 'bg-blue-100 text-blue-800' : '',
    badgeColor: 'bg-cyan-600',
    shortcut: 'H'
  },
  {
    id: 'code',
    name: 'Code',
    icon: CodeBracketIcon,
    count: (!appStore.isCodeRunning && appStore.generatedCode) ? '✓' : null,
    badgeClass: (!appStore.isCodeRunning && appStore.generatedCode) ? 'bg-green-100 text-green-800' : '',
    badgeColor: 'bg-emerald-600',
    shortcut: 'C'
  },
  {
    id: 'table',
    name: 'Table',
    icon: TableCellsIcon,
    count: (appStore.dataframes && appStore.dataframes.length) ? String(appStore.dataframes.length) : null,
    badgeClass: (appStore.dataframes && appStore.dataframes.length) ? 'bg-blue-100 text-blue-800' : '',
    badgeColor: 'bg-sky-600',
    shortcut: 'T'
  },
  {
    id: 'figure',
    name: 'Figure',
    icon: ChartBarIcon,
    count: (appStore.figures && appStore.figures.length) ? String(appStore.figures.length) : null,
    badgeClass: (appStore.figures && appStore.figures.length) ? 'bg-purple-100 text-purple-800' : '',
    badgeColor: 'bg-fuchsia-600',
    shortcut: 'f'
  },
  {
    id: 'terminal',
    name: 'Console',
    icon: CommandLineIcon,
    count: (appStore.terminalOutput && !appStore.isCodeRunning) ? '1' : null,
    badgeClass: (appStore.terminalOutput && !appStore.isCodeRunning) ? 'bg-gray-100 text-gray-800' : '',
    badgeColor: 'bg-slate-700',
    shortcut: 'O'
  },
  {
    id: 'preview',
    name: 'Preview',
    icon: EyeIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-gray-400',
    shortcut: 'V'
  },
  {
    id: 'schema-editor',
    name: 'Schema',
    icon: DocumentTextIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-gray-400',
    shortcut: 'E'
  }
])

// Flash/pulse when counts increase
const flash = ref({})
const counts = computed(() => ({
  chat: appStore.chatHistory?.length || 0,
  code: (!appStore.isCodeRunning && appStore.generatedCode) ? 1 : 0,
  table: appStore.dataframes?.length || 0,
  figure: appStore.figures?.length || 0,
  terminal: (appStore.terminalOutput && !appStore.isCodeRunning) ? 1 : 0
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

function handleTabClick(id) {
  if (id === 'chat') {
    appStore.toggleChatOverlay()
  } else {
    appStore.setActiveTab(id)
  }
}

// Note: Input field checking is now handled by TopToolbar.vue

// Note: Tab shortcuts are now handled by TopToolbar.vue using Option+letter keys
// This provides a unified shortcut system across the application

// Chat panel resize logic
const isResizing = ref(false)
const containerRef = ref(null)

function startResize(event) {
  isResizing.value = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  // Prevent text selection during drag
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'ew-resize'
}

function onResize(event) {
  if (!isResizing.value) return
  
  // Get the container (relative flex-1 div)
  const container = document.querySelector('.relative.flex-1.overflow-hidden')
  if (!container) return
  
  const containerRect = container.getBoundingClientRect()
  const newWidth = (event.clientX - containerRect.left) / containerRect.width
  
  // Clamp between 15% and 60%
  const clampedWidth = Math.max(0.15, Math.min(0.60, newWidth))
  appStore.chatOverlayWidth = clampedWidth
}

function stopResize() {
  if (isResizing.value) {
    appStore.saveLocalConfig()
  }
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

// Event listeners setup
</script>
