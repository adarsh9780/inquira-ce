<template>
  <div class="flex h-full bg-white overflow-hidden relative">
    
    <!-- Workspace Dual Pane View -->
    <div v-show="appStore.activeTab === 'workspace'" class="flex-1 flex overflow-hidden">
      
      <!-- Left Pane (Chat / Code) -->
      <div 
        class="flex flex-col border-r border-gray-200" 
        :style="{ width: appStore.leftPaneWidth + '%' }"
      >
        <WorkspaceLeftPane />
      </div>

      <!-- Resizer Handle -->
      <div 
        class="w-1.5 bg-gray-100 hover:bg-blue-400 cursor-col-resize z-10 hover:shadow-[0_0_8px_rgba(59,130,246,0.5)] transition-colors"
        @mousedown="startResize"
      ></div>

      <!-- Right Pane (Table / Figure / VarEx) -->
      <div 
        class="flex flex-col flex-1"
        :style="{ width: (100 - appStore.leftPaneWidth) + '%' }"
      >
        <WorkspaceRightPane />
      </div>

    </div>

    <!-- Other Full-Screen Views (Terminal, Preview, Schema) -->
    <div v-show="appStore.activeTab !== 'workspace'" class="relative flex-1 overflow-hidden bg-gray-50/50">
      <div v-show="appStore.activeTab === 'terminal'" class="h-full p-3 sm:p-4">
        <TerminalTab />
      </div>
      <div v-show="appStore.activeTab === 'preview'" class="h-full p-3 sm:p-4">
        <PreviewTab />
      </div>
      <div v-show="appStore.activeTab === 'schema-editor'" class="h-full p-3 sm:p-4">
        <SchemaEditorTab />
      </div>
    </div>
    
    <!-- Resize Overlay (invisible, captures mouse events during drag) -->
    <div 
      v-if="isResizing" 
      class="fixed inset-0 z-50 cursor-col-resize"
      @mousemove="onResize"
      @mouseup="stopResize"
      @mouseleave="stopResize"
    ></div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import WorkspaceLeftPane from './WorkspaceLeftPane.vue'
import WorkspaceRightPane from './WorkspaceRightPane.vue'
import TerminalTab from '../analysis/TerminalTab.vue'
import PreviewTab from '../preview/PreviewTab.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'

const appStore = useAppStore()

// Resizing Logic
const isResizing = ref(false)

function startResize(e) {
  isResizing.value = true
  // Prevent text selection during drag
  document.body.style.userSelect = 'none'
}

function onResize(e) {
  if (!isResizing.value) return
  // Calculate percentage based on window width (assuming full width container minus sidebar)
  // To be precise we calculate against the container's width, but a window based calc is often fine
  // A safer approach:
  const containerWidth = document.body.clientWidth - (appStore.isSidebarCollapsed ? 64 : 256) // Account for sidebar width
  // But wait, the LeftPane starts after the sidebar. We can get the mouse X relative to the screen.
  let newWidthPct = ((e.clientX - (appStore.isSidebarCollapsed ? 64 : 256)) / containerWidth) * 100
  
  // Clamp between 20% and 80%
  if (newWidthPct < 20) newWidthPct = 20
  if (newWidthPct > 80) newWidthPct = 80
  
  appStore.setLeftPaneWidth(newWidthPct)
}

function stopResize() {
  if (isResizing.value) {
    isResizing.value = false
    document.body.style.userSelect = ''
  }
}

onMounted(() => {
  window.addEventListener('mouseup', stopResize)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', stopResize)
})
</script>
