<template>
  <div ref="paneRef" class="flex h-full w-full min-h-0 min-w-0 flex-col" :data-toolbar-mode="toolbarMode" style="background-color: var(--color-workspace-surface);">
    <AppToolbar aria-label="Results toolbar">
      <template #start>
        <SegmentedControl
          v-model="selectedCategory"
          :options="resultCategoryOptions"
          :icon-only="toolbarMode !== 'wide'"
          aria-label="Result views"
        />
      </template>

      <div id="workspace-right-pane-toolbar-center" class="min-w-0"></div>

      <template #end>
        <div id="workspace-right-pane-toolbar-right" class="min-w-0"></div>
      </template>
    </AppToolbar>

    <p class="sr-only" aria-live="polite">{{ resultAnnouncement }}</p>

    <div class="min-h-0 flex-1 p-2.5 pb-0 sm:p-3 sm:pb-0" style="background-color: var(--color-workspace-surface);">
      <TableTab v-if="selectedCategory === 'table'" :toolbar-mode="toolbarMode" />
      <FigureTab v-else-if="selectedCategory === 'chart'" :toolbar-mode="toolbarMode" />
      <OutputTab v-else :toolbar-mode="toolbarMode" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useArtifactStore } from '../../stores/artifactStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useUiStore } from '../../stores/uiStore'
import AppToolbar from '../ui/AppToolbar.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import { buildUserRunItems } from '../../utils/unifiedResults'
import {
  ChartBarIcon,
  PlayCircleIcon,
  TableCellsIcon,
} from '@heroicons/vue/24/outline'

const artifactStore = useArtifactStore()
const conversationStore = useConversationStore()
const executionStore = useExecutionStore()
const uiStore = useUiStore()
const paneRef = ref<HTMLElement | null>(null)
const paneWidth = ref(0)
const resultAnnouncement = ref('')
let paneResizeObserver: ResizeObserver | null = null
const TableTab = defineAsyncComponent(() => import('../analysis/TableTab.vue'))
const FigureTab = defineAsyncComponent(() => import('../analysis/FigureTab.vue'))
const OutputTab = defineAsyncComponent(() => import('../analysis/OutputTab.vue'))
const toolbarMode = computed<'wide' | 'compact' | 'minimal'>(() => {
  if (paneWidth.value >= 900) return 'wide'
  if (paneWidth.value >= 520) return 'compact'
  return 'minimal'
})

const tableResultCount = computed(() => Math.max(
  Number(artifactStore.dataframeCount || 0),
  Array.isArray(artifactStore.dataframes) ? artifactStore.dataframes.length : 0,
))
const chartResultCount = computed(() => Math.max(
  Number(artifactStore.figureCount || 0),
  Array.isArray(artifactStore.figures) ? artifactStore.figures.length : 0,
))
const runResultCount = computed(() => buildUserRunItems({
  terminalEntries: executionStore.terminalEntries,
  conversationId: conversationStore.activeConversationId,
}).length)
const resultCategoryOptions = computed(() => [
  { value: 'table', label: 'Tables', icon: TableCellsIcon, count: tableResultCount.value },
  { value: 'chart', label: 'Charts', icon: ChartBarIcon, count: chartResultCount.value },
  { value: 'runs', label: 'Runs', icon: PlayCircleIcon, count: runResultCount.value },
])

function categoryForPane(pane: unknown): 'table' | 'chart' | 'runs' {
  if (pane === 'table') return 'table'
  if (pane === 'figure') return 'chart'
  return 'runs'
}

function paneForCategory(category: unknown): 'table' | 'figure' | 'output' {
  if (category === 'table') return 'table'
  if (category === 'chart') return 'figure'
  return 'output'
}

const selectedCategory = computed({
  get: () => categoryForPane(uiStore.dataPane),
  set: (category) => {
    const normalized = ['table', 'chart', 'runs'].includes(category) ? category : 'runs'
    uiStore.setDataPane(paneForCategory(normalized))
    const selected = resultCategoryOptions.value.find((option) => option.value === normalized)
    resultAnnouncement.value = selected ? `${selected.label} selected` : ''
  },
})

watch(() => uiStore.dataPane, (pane, previousPane) => {
  if (pane === previousPane) return
  const category = categoryForPane(pane)
  const selected = resultCategoryOptions.value.find((option) => option.value === category)
  resultAnnouncement.value = selected ? `${selected.label} available` : ''
})

onMounted(() => {
  if (!('ResizeObserver' in window) || !paneRef.value) return
  paneResizeObserver = new ResizeObserver(([entry]) => {
    paneWidth.value = Number(entry?.contentRect?.width || paneRef.value?.clientWidth || 0)
  })
  paneResizeObserver.observe(paneRef.value)
})

onBeforeUnmount(() => paneResizeObserver?.disconnect())
</script>
