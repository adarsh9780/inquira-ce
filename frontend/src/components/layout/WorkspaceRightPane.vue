<template>
  <div class="flex h-full flex-col" style="background-color: var(--color-surface);">
    <div ref="headerRef" class="flex-shrink-0 h-16 border-b px-4 flex items-center gap-4" style="background-color: var(--color-base); border-color: var(--color-border);">
      <div class="flex-shrink-0">
        <HeaderDropdown
          v-if="useCompactPaneSwitcher"
          v-model="selectedDataPane"
          :options="dataPaneOptions"
          placeholder="Data view"
          aria-label="Select data pane"
          max-width-class="w-[150px]"
        />
        <div v-else class="inline-flex rounded-lg border p-1" style="border-color: var(--color-border); background-color: var(--color-base);">
          <button
            @click="appStore.setDataPane('table')"
            class="rounded-md p-2 transition-colors flex items-center justify-center"
            :class="appStore.dataPane === 'table' ? 'bg-white shadow-sm' : ''"
            :style="appStore.dataPane === 'table' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
            title="Table"
            aria-label="Table"
          >
            <TableCellsIcon class="w-4 h-4" />
            <span class="sr-only">Table</span>
          </button>
          <button
            @click="appStore.setDataPane('figure')"
            class="rounded-md p-2 transition-colors flex items-center justify-center"
            :class="appStore.dataPane === 'figure' ? 'bg-white shadow-sm' : ''"
            :style="appStore.dataPane === 'figure' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
            title="Chart"
            aria-label="Chart"
          >
            <ChartBarIcon class="w-4 h-4" />
            <span class="sr-only">Chart</span>
          </button>
          <button
            @click="appStore.setDataPane('output')"
            class="rounded-md p-2 transition-colors flex items-center justify-center"
            :class="appStore.dataPane === 'output' ? 'bg-white shadow-sm' : ''"
            :style="appStore.dataPane === 'output' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
            title="Output"
            aria-label="Output"
          >
            <CommandLineIcon class="w-4 h-4" />
            <span class="sr-only">Output</span>
          </button>
        </div>
      </div>
      
      <!-- Teleport Target for Table/Figure/Output Toolbar -->
      <div id="workspace-right-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end"></div>
    </div>

    <div class="min-h-0 flex-1 p-3 sm:p-4 pb-0" style="background-color: var(--color-base);">
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
