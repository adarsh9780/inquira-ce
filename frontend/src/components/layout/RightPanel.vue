  <div class="flex flex-col h-full bg-white overflow-hidden relative">
    
    <!-- Top Workspace Area (Chat/Code & Data Panes) -->
    <div 
      v-show="appStore.activeTab === 'workspace'" 
      class="flex w-full overflow-hidden"
      :style="{ height: appStore.isTerminalOpen ? (100 - appStore.terminalHeight) + '%' : '100%' }"
    >
      <!-- Left Pane (Chat / Code) -->
      <div 
        class="flex flex-col h-full border-r border-gray-200" 
        :style="{ width: appStore.leftPaneWidth + '%' }"
      >
        <WorkspaceLeftPane />
      </div>

      <!-- Vertical Resizer Handle (Left/Right panes) -->
      <div 
        class="w-[3px] h-full hover:w-1 bg-transparent hover:bg-blue-400 cursor-col-resize z-10 transition-all duration-150 relative -mx-[1px] hover:shadow-[0_0_8px_rgba(59,130,246,0.5)]"
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
      class="h-[3px] w-full hover:h-1 bg-transparent hover:bg-blue-400 cursor-row-resize z-20 transition-all duration-150 relative -my-[1px] hover:shadow-[0_0_8px_rgba(59,130,246,0.5)]"
      @mousedown="startResizeY"
    ></div>

    <!-- Bottom Pane (Terminal View) -->
    <div
      v-show="appStore.isTerminalOpen && appStore.activeTab === 'workspace'"
      class="w-full flex flex-col bg-white border-t border-gray-200 z-10 overflow-hidden"
      :style="{ height: appStore.terminalHeight + '%' }"
    >
      <div class="flex justify-between items-center px-4 py-1.5 bg-gray-50 border-b border-gray-200">
        <div class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
          <CommandLineIcon class="w-3.5 h-3.5" />
          Terminal
        </div>
        <button 
          @click="appStore.toggleTerminal()" 
          class="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-200 transition-colors"
          title="Close Terminal"
        >
          <XMarkIcon class="w-4 h-4" />
        </button>
      </div>
      <div class="flex-1 overflow-hidden relative p-1 pb-3">
        <TerminalTab />
      </div>
    </div>

    <!-- Other Full-Screen Views (Preview, Schema) -->
    <div v-show="appStore.activeTab !== 'workspace'" class="relative flex-1 overflow-hidden bg-gray-50/50">
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
import PreviewTab from '../preview/PreviewTab.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'
import { CommandLineIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()

// Resizing Logic
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
  if (isResizingX.value) {
    const containerWidth = document.body.clientWidth - (appStore.isSidebarCollapsed ? 64 : 256)
    let newWidthPct = ((e.clientX - (appStore.isSidebarCollapsed ? 64 : 256)) / containerWidth) * 100
    
    if (newWidthPct < 20) newWidthPct = 20
    if (newWidthPct > 80) newWidthPct = 80
    
    appStore.setLeftPaneWidth(newWidthPct)
  }
  
  if (isResizingY.value) {
    // Determine height based on mouse Y relative to window height.
    // The top UI header is roughly 64px, container height can be assumed full window height.
    let rootHeight = document.body.clientHeight
    let mouseFromBottom = rootHeight - e.clientY
    let newHeightPct = (mouseFromBottom / rootHeight) * 100

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
