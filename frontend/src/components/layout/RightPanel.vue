<template>
  <div ref="panelRef" class="flex flex-col h-full overflow-hidden relative workspace-shell-panel" style="background-color: var(--color-workspace-surface);">
    
    <!-- Top Workspace Area (Chat/Code & Data Panes) -->
    <div 
      v-show="isWorkspaceActive"
      class="flex w-full overflow-hidden transition-[height] motion-slow"
      :style="{ height: workspaceVisualHeight + '%' }"
    >
      <!-- Left Pane (Chat / Code) -->
      <div 
        v-if="!appStore.isDataFocusMode"
        class="flex flex-col h-full border-r workspace-center-pane" 
        :style="{ width: appStore.leftPaneWidth + '%', borderColor: 'var(--color-border)' }"
      >
        <WorkspaceLeftPane />
      </div>

      <!-- Vertical Resizer Handle (Left/Right panes) -->
      <div 
        v-if="!appStore.isDataFocusMode"
        class="pane-resizer-x relative z-10 -mx-[1px] h-full w-[3px] cursor-col-resize bg-transparent transition-all motion-fast hover:w-1"
        @mousedown="startResizeX"
      ></div>

      <!-- Right Pane (Table / Figure / Output) -->
      <div 
        class="flex flex-col h-full workspace-data-pane"
        :style="{ width: rightPaneWidth + '%' }"
      >
        <WorkspaceRightPane />
      </div>
    </div>

    <!-- Horizontal Resizer Handle (Workspace/Terminal panes) -->
    <div
      v-if="isWorkspaceActive"
      class="pane-resizer-y relative z-20 -my-[1px] w-full bg-transparent transition-[height,opacity,background-color,box-shadow] motion-slow"
      :class="appStore.isTerminalOpen ? 'h-[3px] cursor-row-resize opacity-100 hover:h-1' : 'h-0 pointer-events-none opacity-0'"
      @mousedown="appStore.isTerminalOpen && startResizeY($event)"
    ></div>

    <!-- Bottom Pane (Terminal View) -->
    <div
      v-if="isWorkspaceActive"
      class="w-full flex flex-col border-t z-10 overflow-hidden transition-[height,opacity,border-color] motion-slow"
      :class="appStore.isTerminalOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'"
      :style="{ height: terminalVisualHeight + '%', borderColor: appStore.isTerminalOpen ? 'var(--color-border)' : 'transparent', backgroundColor: 'var(--color-workspace-surface)' }"
    >
      <div class="flex h-7 justify-between items-center px-3 border-b" style="background-color: var(--color-workspace-surface); border-color: var(--color-border);">
        <div class="text-[10px] font-medium uppercase tracking-wide flex items-center gap-1" style="color: var(--color-text-muted);">
          <CommandLineIcon class="w-3.5 h-3.5" />
          Terminal
        </div>
        
        <!-- Teleport Target for Terminal Toolbar -->
        <div id="terminal-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-2 mr-1"></div>

        <button 
          @click="appStore.toggleTerminal()" 
          class="btn-icon h-5 w-5 p-1"
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
    <div v-show="appStore.activeTab !== 'workspace'" class="relative flex-1 overflow-hidden" style="background-color: var(--color-workspace-surface);">
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import WorkspaceLeftPane from './WorkspaceLeftPane.vue'
import WorkspaceRightPane from './WorkspaceRightPane.vue'
import TerminalTab from '../analysis/TerminalTab.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'
import { CommandLineIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const isWorkspaceActive = computed(() => appStore.activeTab === 'workspace')
const rightPaneWidth = computed(() => appStore.isDataFocusMode ? 100 : (100 - appStore.leftPaneWidth))
const terminalVisualHeight = computed(() => {
  if (!isWorkspaceActive.value) return 0
  return appStore.isTerminalOpen ? appStore.terminalHeight : 0
})
const workspaceVisualHeight = computed(() => 100 - terminalVisualHeight.value)

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

<style scoped>
.workspace-shell-panel {
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--color-text-main) 3%, transparent);
}

.workspace-center-pane {
  background-color: var(--color-workspace-surface);
  box-shadow: inset -1px 0 0 color-mix(in srgb, var(--color-text-main) 3%, transparent);
}

.workspace-data-pane {
  background-color: var(--color-workspace-surface);
  box-shadow: inset 1px 0 0 color-mix(in srgb, var(--color-text-main) 2%, transparent);
}

.pane-resizer-x:hover,
.pane-resizer-y:hover {
  background-color: var(--color-border-hover);
  box-shadow: 0 0 6px color-mix(in srgb, var(--color-text-main) 15%, transparent);
}
</style>
