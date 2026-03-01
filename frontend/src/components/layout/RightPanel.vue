<template>
  <div ref="panelRef" class="flex flex-col h-full overflow-hidden relative" style="background-color: var(--color-base);">
    
    <!-- Top Workspace Area (Chat/Code & Data Panes) -->
    <div 
      v-show="appStore.activeTab === 'workspace'" 
      class="flex w-full overflow-hidden"
      :style="{ height: appStore.isTerminalOpen ? (100 - appStore.terminalHeight) + '%' : '100%' }"
    >
      <!-- Left Pane (Chat / Code) -->
      <div 
        class="flex flex-col h-full border-r" 
        :style="{ width: appStore.leftPaneWidth + '%', borderColor: 'var(--color-border)' }"
      >
        <WorkspaceLeftPane />
      </div>

      <!-- Vertical Resizer Handle (Left/Right panes) -->
      <div 
        class="w-[3px] h-full hover:w-1 bg-transparent hover:bg-zinc-300 cursor-col-resize z-10 transition-all duration-150 relative -mx-[1px] hover:shadow-[0_0_6px_rgba(0,0,0,0.15)]"
        @mousedown="startResizeX"
      ></div>

      <!-- Right Pane (Table / Figure / VarEx) -->
      <div 
        class="flex flex-col h-full"
        :style="{ width: (100 - appStore.leftPaneWidth) + '%' }"
      >
        <WorkspaceRightPane />
      </div>
    </div>

    <!-- Horizontal Resizer Handle (Workspace/Terminal panes) -->
    <div
      v-show="appStore.activeTab === 'workspace' && appStore.isTerminalOpen"
      class="h-[3px] w-full hover:h-1 bg-transparent hover:bg-zinc-300 cursor-row-resize z-20 transition-all duration-150 relative -my-[1px] hover:shadow-[0_0_6px_rgba(0,0,0,0.15)]"
      @mousedown="startResizeY"
    ></div>

    <!-- Bottom Pane (Terminal View) -->
    <div
      v-show="appStore.isTerminalOpen && appStore.activeTab === 'workspace'"
      class="w-full flex flex-col border-t z-10 overflow-hidden"
      :style="{ height: appStore.terminalHeight + '%', borderColor: 'var(--color-border)', backgroundColor: 'var(--color-base)' }"
    >
      <div class="flex justify-between items-center px-4 py-1.5 border-b" style="background-color: var(--color-base); border-color: var(--color-border);">
        <div class="text-[10px] font-semibold uppercase tracking-wider flex items-center gap-1.5" style="color: var(--color-text-muted);">
          <CommandLineIcon class="w-3.5 h-3.5" />
          Terminal
        </div>
        
        <!-- Teleport Target for Terminal Toolbar -->
        <div id="terminal-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-4 mr-2"></div>

        <button 
          @click="appStore.toggleTerminal()" 
          class="btn-icon"
          title="Close Terminal"
        >
          <XMarkIcon class="w-4 h-4" />
        </button>
      </div>
      <div class="flex-1 overflow-hidden relative p-1 pb-3">
        <TerminalTab />
      </div>
    </div>

    <!-- Other Full-Screen Views (Schema) -->
    <div v-show="appStore.activeTab !== 'workspace'" class="relative flex-1 overflow-hidden" style="background-color: var(--color-base);">
      <div v-show="appStore.activeTab === 'schema-editor'" class="h-full p-3 sm:p-4">
        <SchemaEditorTab />
      </div>
    </div>
    
    <!-- Resize Overlay (invisible, captures mouse events during drag) -->
    <div 
      v-if="isResizingX || isResizingY" 
      class="fixed inset-0 z-50 cursor-col-resize"
      :class="isResizingY ? 'cursor-row-resize' : 'cursor-col-resize'"
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
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'
import { CommandLineIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()

// Resizing Logic
const panelRef = ref(null)
const isResizingX = ref(false)
const isResizingY = ref(false)

function startResizeX(e) {
  isResizingX.value = true
  document.body.style.userSelect = 'none'
}

function startResizeY(e) {
  isResizingY.value = true
  document.body.style.userSelect = 'none'
}

function onResize(e) {
  const panelRect = panelRef.value?.getBoundingClientRect?.()
  if (!panelRect || panelRect.width <= 0 || panelRect.height <= 0) return

  if (isResizingX.value) {
    let newWidthPct = ((e.clientX - panelRect.left) / panelRect.width) * 100
    
    if (newWidthPct < 20) newWidthPct = 20
    if (newWidthPct > 80) newWidthPct = 80
    
    appStore.setLeftPaneWidth(newWidthPct)
  }
  
  if (isResizingY.value) {
    const mouseFromBottom = panelRect.bottom - e.clientY
    let newHeightPct = (mouseFromBottom / panelRect.height) * 100

    if (newHeightPct < 10) newHeightPct = 10
    if (newHeightPct > 80) newHeightPct = 80
    
    appStore.setTerminalHeight(newHeightPct)
  }
}

function stopResize() {
  if (isResizingX.value || isResizingY.value) {
    isResizingX.value = false
    isResizingY.value = false
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
