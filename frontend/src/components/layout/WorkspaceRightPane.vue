<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <AppToolbar ref="headerRef" aria-label="Results pane toolbar">
      <template #start>
        <HeaderDropdown
          v-if="useCompactPaneSwitcher"
          v-model="selectedDataPane"
          :options="dataPaneOptions"
          placeholder="Data view"
          aria-label="Select data pane"
          max-width-class="w-[150px]"
        />
        <SegmentedControl v-else v-model="selectedDataPane" :options="dataPaneOptions" aria-label="Result panes" />
      </template>

      <!-- Teleport Target: centered selector slot -->
      <div id="workspace-right-pane-toolbar-center" class="min-w-0"></div>

      <!-- Teleport Target: right controls slot -->
      <template #end><div id="workspace-right-pane-toolbar-right" class="min-w-0"></div></template>
    </AppToolbar>

    <p class="sr-only" aria-live="polite">{{ resultAnnouncement }}</p>
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
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import AppToolbar from '../ui/AppToolbar.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import {
  TableCellsIcon,
  ChartBarIcon,
  CommandLineIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const headerRef = ref(null)
const useCompactPaneSwitcher = ref(false)
const isMounted = ref(false)
const newResultPanes = ref(new Set())
const resultAnnouncement = ref('')
let switcherResizeObserver = null
const COMPACT_SWITCHER_THRESHOLD_PX = 660
const TableTab = defineAsyncComponent(() => import('../analysis/TableTab.vue'))
const FigureTab = defineAsyncComponent(() => import('../analysis/FigureTab.vue'))
const OutputTab = defineAsyncComponent(() => import('../analysis/OutputTab.vue'))

const dataPaneOptions = computed(() => [
  { value: 'table', label: 'Table', icon: TableCellsIcon, indicator: newResultPanes.value.has('table') },
  { value: 'figure', label: 'Chart', icon: ChartBarIcon, indicator: newResultPanes.value.has('figure') },
  { value: 'output', label: 'Output', icon: CommandLineIcon, indicator: newResultPanes.value.has('output') }
])

const selectedDataPane = computed({
  get: () => appStore.dataPane,
  set: (pane) => {
    newResultPanes.value.delete(pane)
    newResultPanes.value = new Set(newResultPanes.value)
    appStore.setDataPane(pane)
  }
})

function markResultAvailable(pane, label) {
  if (!isMounted.value || appStore.dataPane === pane) return
  newResultPanes.value = new Set([...newResultPanes.value, pane])
  resultAnnouncement.value = `${label} available`
}

watch(() => appStore.tableCount, (next, previous) => {
  if (Number(next) > Number(previous || 0)) markResultAvailable('table', 'New table')
})
watch(() => appStore.figureCount, (next, previous) => {
  if (Number(next) > Number(previous || 0)) markResultAvailable('figure', 'New chart')
})
watch(() => appStore.terminalEntries.length, (next, previous) => {
  if (Number(next) > Number(previous || 0)) markResultAvailable('output', 'New output')
})

function updatePaneSwitcherMode() {
  const width = Number(headerRef.value?.$el?.clientWidth || headerRef.value?.clientWidth || 0)
  useCompactPaneSwitcher.value = width > 0 && width < COMPACT_SWITCHER_THRESHOLD_PX
}

onMounted(() => {
  isMounted.value = true
  updatePaneSwitcherMode()
  const element = headerRef.value?.$el || headerRef.value
  if ('ResizeObserver' in window && element) {
    switcherResizeObserver = new ResizeObserver(() => updatePaneSwitcherMode())
    switcherResizeObserver.observe(element)
  }
})

onUnmounted(() => {
  isMounted.value = false
  const element = headerRef.value?.$el || headerRef.value
  if (switcherResizeObserver && element) {
    try { switcherResizeObserver.unobserve(element) } catch (_error) {}
  }
  switcherResizeObserver = null
})
</script>
