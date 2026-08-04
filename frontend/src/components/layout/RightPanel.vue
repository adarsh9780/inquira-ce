<template>
  <div ref="panelRef" class="flex flex-col h-full overflow-hidden relative workspace-shell-panel" style="background-color: var(--color-workspace-surface);">

    <!-- Top Workspace Area (Chat/Code & Data Panes) -->
    <div
      v-show="isWorkspaceActive"
      class="relative flex w-full flex-col transition-[height] motion-slow"
      :style="{ height: workspaceVisualHeight + '%' }"
    >
      <WorkspaceContextBar :compact="isCompactLayout" />

      <div
        class="relative flex min-h-0 w-full flex-1 overflow-hidden"
        :class="isCompactLayout ? 'flex-col' : ''"
      >
        <div v-if="isCompactLayout" class="flex h-9 shrink-0 items-center justify-center gap-1 border-b border-[var(--color-border)]">
          <button type="button" class="compact-pane-button" :aria-pressed="compactPane === 'work'" @click="compactPane = 'work'">Work</button>
          <button type="button" class="compact-pane-button" :aria-pressed="compactPane === 'data'" @click="compactPane = 'data'">Data</button>
        </div>
        <!-- Left Pane (Chat / Code) -->
        <div
          class="flex h-full min-w-0 flex-col border-r workspace-center-pane"
          v-show="!isCompactLayout || compactPane === 'work'"
          :style="{ width: isCompactLayout ? '100%' : leftPaneWidth + '%', height: isCompactLayout ? 'calc(100% - 2.25rem)' : '100%', borderColor: 'var(--color-border)' }"
        >
          <WorkspaceLeftPane />
        </div>

        <!-- Vertical Resizer Handle (Left/Right panes) -->
        <div
          class="pane-resizer-x relative z-10 -mx-[1px] h-full w-[3px] cursor-col-resize bg-transparent transition-all motion-fast hover:w-1"
          v-if="!isCompactLayout"
          role="separator"
          aria-label="Resize work and data panes"
          aria-orientation="vertical"
          :aria-valuenow="Math.round(leftPaneWidth)"
          tabindex="0"
          @pointerdown="startResizeX"
          @keydown="handleResizeXKeydown"
        ></div>

        <!-- Right Pane (Table / Figure / Output) -->
        <div
          class="flex h-full min-w-0 flex-col overflow-hidden workspace-data-pane"
          v-show="!isCompactLayout || compactPane === 'data'"
          :style="{
            width: isCompactLayout ? '100%' : `${rightPaneWidth}%`,
            height: isCompactLayout ? 'calc(100% - 2.25rem)' : '100%',
            opacity: 1
          }"
        >
          <WorkspaceRightPane />
        </div>
      </div>
    </div>

    <!-- Horizontal Resizer Handle (Workspace/Terminal panes) -->
    <div
      v-if="isWorkspaceActive"
      class="pane-resizer-y relative z-20 -my-[1px] w-full bg-transparent transition-[height,opacity,background-color,box-shadow] motion-slow"
      :class="uiStore.isTerminalOpen ? 'h-[3px] cursor-row-resize opacity-100 hover:h-1' : 'h-0 pointer-events-none opacity-0'"
      role="separator"
      aria-label="Resize workspace and terminal panes"
      aria-orientation="horizontal"
      :aria-valuenow="Math.round(terminalVisualHeight)"
      :tabindex="uiStore.isTerminalOpen ? 0 : -1"
      @pointerdown="uiStore.isTerminalOpen && startResizeY($event)"
      @keydown="handleResizeYKeydown"
    ></div>

    <!-- Bottom Pane (Terminal View) -->
    <div
      v-if="isWorkspaceActive"
      class="w-full flex flex-col border-t z-10 overflow-hidden transition-[height,opacity,border-color] motion-slow"
      :class="uiStore.isTerminalOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'"
      :style="{ height: terminalVisualHeight + '%', borderColor: uiStore.isTerminalOpen ? 'var(--color-border)' : 'transparent', backgroundColor: 'var(--color-workspace-surface)' }"
    >
      <div class="flex h-7 justify-between items-center px-3 border-b" style="background-color: var(--color-workspace-surface); border-color: var(--color-border);">
        <div class="text-[10px] font-medium uppercase tracking-wide flex items-center gap-1" style="color: var(--color-text-muted);">
          <CommandLineIcon class="w-3.5 h-3.5" />
          Terminal
        </div>

        <!-- Teleport Target for Terminal Toolbar -->
        <div id="terminal-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-2 mr-1"></div>

        <button
          @click="uiStore.toggleTerminal()"
          class="btn-icon h-5 w-5 p-1"
          title="Close Terminal"
          aria-label="Close terminal"
          data-tooltip="Close terminal"
        >
          <XMarkIcon class="w-4 h-4" />
        </button>
      </div>
      <div class="flex-1 overflow-hidden relative p-1 pb-3">
        <TerminalTab />
      </div>
    </div>

    <!-- Other Full-Screen Views -->
    <div v-show="uiStore.activeTab !== 'workspace'" class="relative flex-1 overflow-hidden" style="background-color: var(--color-workspace-surface);">
      <div v-show="uiStore.activeTab === 'schema-editor'" class="h-full p-3 sm:p-4">
        <SchemaEditorTab />
      </div>
      <div v-show="uiStore.activeTab === 'conversation-tree'" class="flex h-full min-h-0 flex-col p-3 sm:p-4">
        <div class="mb-3 flex h-9 shrink-0 items-center justify-between">
          <div class="min-w-0">
            <h2 class="truncate text-sm font-semibold text-[var(--color-text-main)]">Conversation Tree</h2>
            <p class="truncate text-[11px] text-[var(--color-text-muted)]">Browse turns, branches, and saved outputs.</p>
          </div>
        </div>
        <SidebarGlobalTurnTree variant="page" />
      </div>
    </div>

    <!-- Resize Overlay (invisible, captures mouse events during drag) -->
    <div
      v-if="isResizingX || isResizingY"
      class="fixed inset-0 z-50 cursor-col-resize"
      :class="isResizingY ? 'cursor-row-resize' : 'cursor-col-resize'"
      @mousemove="onResize"
      @pointermove="onResize"
      @mouseup="stopResize"
      @pointerup="stopResize"
      @mouseleave="stopResize"
    ></div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent, onMounted, onUnmounted } from 'vue'
import { useUiStore } from '../../stores/uiStore'
import WorkspaceLeftPane from './WorkspaceLeftPane.vue'
import WorkspaceRightPane from './WorkspaceRightPane.vue'
import WorkspaceContextBar from './WorkspaceContextBar.vue'
import SidebarGlobalTurnTree from './sidebar/SidebarGlobalTurnTree.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'
import { CommandLineIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const uiStore = useUiStore()
const TerminalTab = defineAsyncComponent(() => import('../analysis/TerminalTab.vue'))
const isWorkspaceActive = computed(() => uiStore.activeTab === 'workspace')
const leftPaneWidth = computed(() => uiStore.leftPaneWidth)
const rightPaneWidth = computed(() => 100 - uiStore.leftPaneWidth)
const terminalVisualHeight = computed(() => {
  if (!isWorkspaceActive.value) return 0
  return uiStore.isTerminalOpen ? uiStore.terminalHeight : 0
})
const workspaceVisualHeight = computed(() => 100 - terminalVisualHeight.value)

// Resizing Logic
const panelRef = ref<HTMLElement | null>(null)
const isResizingX = ref(false)
const isResizingY = ref(false)
// Start in the safe compact state so the first frame cannot overlap before
// ResizeObserver reports the real workspace width.
const isCompactLayout = ref(true)
const compactPane = ref('work')
let panelResizeObserver: ResizeObserver | null = null

function startResizeX(_event: PointerEvent) {
  isResizingX.value = true
  document.body.style.userSelect = 'none'
}

function startResizeY(_event: PointerEvent) {
  isResizingY.value = true
  document.body.style.userSelect = 'none'
}

function handleResizeXKeydown(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Home') uiStore.setLeftPaneWidth(20)
  else if (event.key === 'End') uiStore.setLeftPaneWidth(80)
  else uiStore.setLeftPaneWidth(Math.min(80, Math.max(20, leftPaneWidth.value + (event.key === 'ArrowRight' ? 2 : -2))))
}

function handleResizeYKeydown(event: KeyboardEvent) {
  if (!uiStore.isTerminalOpen || !['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Home') uiStore.setTerminalHeight(10)
  else if (event.key === 'End') uiStore.setTerminalHeight(80)
  else uiStore.setTerminalHeight(Math.min(80, Math.max(10, terminalVisualHeight.value + (event.key === 'ArrowUp' ? 2 : -2))))
}

function onResize(e: MouseEvent | PointerEvent) {
  const panelRect = panelRef.value?.getBoundingClientRect?.()
  if (!panelRect || panelRect.width <= 0 || panelRect.height <= 0) return

  if (isResizingX.value) {
    let newWidthPct = ((e.clientX - panelRect.left) / panelRect.width) * 100

    if (newWidthPct < 20) newWidthPct = 20
    if (newWidthPct > 80) newWidthPct = 80

    uiStore.setLeftPaneWidth(newWidthPct)
  }

  if (isResizingY.value) {
    const mouseFromBottom = panelRect.bottom - e.clientY
    let newHeightPct = (mouseFromBottom / panelRect.height) * 100

    if (newHeightPct < 10) newHeightPct = 10
    if (newHeightPct > 80) newHeightPct = 80

    uiStore.setTerminalHeight(newHeightPct)
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
  window.addEventListener('pointerup', stopResize)
  if ('ResizeObserver' in window && panelRef.value) {
    panelResizeObserver = new ResizeObserver(([entry]) => {
      isCompactLayout.value = Number(entry?.contentRect?.width || panelRef.value?.clientWidth || 0) < 760
    })
    panelResizeObserver.observe(panelRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('mouseup', stopResize)
  window.removeEventListener('pointerup', stopResize)
  panelResizeObserver?.disconnect?.()
  document.body.style.userSelect = ''
})
</script>

<style scoped>
.workspace-shell-panel {
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--color-text-main) 4%, transparent);
}

.workspace-center-pane {
  background-color: var(--color-workspace-surface);
  box-shadow: inset -1px 0 0 color-mix(in srgb, var(--color-text-main) 3%, transparent);
  transition: width var(--motion-duration-standard) var(--motion-ease-spring), border-color var(--motion-duration-fast) var(--motion-ease-standard);
}

.workspace-data-pane {
  background-color: var(--color-workspace-surface);
  box-shadow: inset 1px 0 0 color-mix(in srgb, var(--color-text-main) 2%, transparent);
  transition: width var(--motion-duration-standard) var(--motion-ease-spring), opacity var(--motion-duration-fast) var(--motion-ease-standard);
  will-change: width, opacity;
}

.pane-resizer-x:hover,
.pane-resizer-y:hover,
.pane-resizer-x:focus-visible,
.pane-resizer-y:focus-visible {
  background-color: var(--color-border-hover);
  box-shadow: 0 0 6px color-mix(in srgb, var(--color-text-main) 15%, transparent);
}

.pane-resizer-x,
.pane-resizer-y {
  touch-action: none;
}

.compact-pane-button {
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.3rem 0.75rem;
}

.compact-pane-button[aria-pressed='true'] {
  background: var(--color-selected-surface);
  color: var(--color-text-main);
}
</style>
