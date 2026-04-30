<template>
  <div class="flex h-full flex-col" style="background-color: var(--color-workspace-surface);">
    <div
      ref="headerRef"
      class="workspace-toolbar-shell flex-shrink-0 h-16 px-3 flex items-center border-b"
      style="background-color: var(--color-workspace-surface); border-color: var(--color-border);"
    >
      <div class="workspace-toolbar-zone workspace-toolbar-zone-left">
        <HeaderDropdown
          v-if="useCompactPaneSwitcher"
          v-model="selectedDataPane"
          :options="dataPaneOptions"
          placeholder="Data view"
          aria-label="Select data pane"
          max-width-class="w-[150px]"
        />
        <div v-else class="inline-flex rounded-xl border p-1" style="border-color: var(--color-border); background-color: var(--color-control-surface);">
          <button
            @click="appStore.setDataPane('table')"
            class="rounded-lg px-3 py-2 transition-colors flex items-center justify-center gap-1.5"
            :style="appStore.dataPane === 'table'
              ? 'background-color: var(--color-selected-surface); color: var(--color-text-main); box-shadow: inset 0 0 0 1px var(--color-selected-border);'
              : 'color: var(--color-text-muted);'"
            title="Table"
            aria-label="Table"
          >
            <TableCellsIcon class="w-4 h-4" />
            <span class="text-xs font-medium">Table</span>
          </button>
          <button
            @click="appStore.setDataPane('figure')"
            class="rounded-lg px-3 py-2 transition-colors flex items-center justify-center gap-1.5"
            :style="appStore.dataPane === 'figure'
              ? 'background-color: var(--color-selected-surface); color: var(--color-text-main); box-shadow: inset 0 0 0 1px var(--color-selected-border);'
              : 'color: var(--color-text-muted);'"
            title="Chart"
            aria-label="Chart"
          >
            <ChartBarIcon class="w-4 h-4" />
            <span class="text-xs font-medium">Chart</span>
          </button>
          <button
            @click="appStore.setDataPane('output')"
            class="rounded-lg px-3 py-2 transition-colors flex items-center justify-center gap-1.5"
            :style="appStore.dataPane === 'output'
              ? 'background-color: var(--color-selected-surface); color: var(--color-text-main); box-shadow: inset 0 0 0 1px var(--color-selected-border);'
              : 'color: var(--color-text-muted);'"
            title="Output"
            aria-label="Output"
          >
            <CommandLineIcon class="w-4 h-4" />
            <span class="text-xs font-medium">Output</span>
          </button>
        </div>
      </div>

      <div class="workspace-toolbar-divider" aria-hidden="true"></div>

      <!-- Teleport Target: centered selector slot -->
      <div id="workspace-right-pane-toolbar-center" class="workspace-toolbar-zone workspace-toolbar-zone-center"></div>

      <div class="workspace-toolbar-divider" aria-hidden="true"></div>

      <!-- Teleport Target: right controls slot -->
      <div id="workspace-right-pane-toolbar-right" class="workspace-toolbar-zone workspace-toolbar-zone-right"></div>
    </div>

    <div class="min-h-0 flex-1 p-3 sm:p-4 pb-0" style="background-color: var(--color-workspace-surface);">
      <div v-if="appStore.dataPane === 'table'" class="h-full">
        <TableTab />
      </div>
      <div v-else-if="appStore.dataPane === 'figure'" class="h-full">
        <FigureTab />
      </div>
      <div v-else class="h-full">
        <OutputTab />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAppStore } from '../../stores/appStore'
import TableTab from '../analysis/TableTab.vue'
import FigureTab from '../analysis/FigureTab.vue'
import OutputTab from '../analysis/OutputTab.vue'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import {
  TableCellsIcon,
  ChartBarIcon,
  CommandLineIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const headerRef = ref(null)
const useCompactPaneSwitcher = ref(false)
let switcherResizeObserver = null
const COMPACT_SWITCHER_THRESHOLD_PX = 660

const dataPaneOptions = [
  { value: 'table', label: 'Table' },
  { value: 'figure', label: 'Chart' },
  { value: 'output', label: 'Output' }
]

const selectedDataPane = computed({
  get: () => appStore.dataPane,
  set: (pane) => appStore.setDataPane(pane)
})

function updatePaneSwitcherMode() {
  const width = Number(headerRef.value?.clientWidth || 0)
  useCompactPaneSwitcher.value = width > 0 && width < COMPACT_SWITCHER_THRESHOLD_PX
}

onMounted(() => {
  updatePaneSwitcherMode()
  if ('ResizeObserver' in window && headerRef.value) {
    switcherResizeObserver = new ResizeObserver(() => updatePaneSwitcherMode())
    switcherResizeObserver.observe(headerRef.value)
  }
})

onUnmounted(() => {
  if (switcherResizeObserver && headerRef.value) {
    try { switcherResizeObserver.unobserve(headerRef.value) } catch (_error) {}
  }
  switcherResizeObserver = null
})
</script>

<style scoped>
.workspace-toolbar-shell {
  gap: 0.5rem;
}

.workspace-toolbar-zone {
  min-width: 0;
  height: 100%;
  display: flex;
  align-items: center;
}

.workspace-toolbar-zone-left {
  justify-content: flex-start;
  flex: 0 0 auto;
  padding-right: 0.25rem;
}

.workspace-toolbar-zone-center {
  justify-content: center;
  flex: 1 1 auto;
}

.workspace-toolbar-zone-right {
  justify-content: flex-end;
  flex: 1 1 auto;
}

.workspace-toolbar-divider {
  width: 1px;
  height: 1.75rem;
  background-color: var(--color-border);
}
</style>
