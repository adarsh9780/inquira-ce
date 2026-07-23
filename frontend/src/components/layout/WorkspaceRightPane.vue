<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <AppToolbar aria-label="Results toolbar">
      <template #start>
        <SegmentedControl
          v-model="selectedCategory"
          :options="resultCategoryOptions"
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
      <TableTab v-if="selectedCategory === 'table'" />
      <FigureTab v-else-if="selectedCategory === 'chart'" />
      <OutputTab v-else />
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import AppToolbar from '../ui/AppToolbar.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import { buildUserRunItems } from '../../utils/unifiedResults'
import {
  ChartBarIcon,
  PlayCircleIcon,
  TableCellsIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const resultAnnouncement = ref('')
const TableTab = defineAsyncComponent(() => import('../analysis/TableTab.vue'))
const FigureTab = defineAsyncComponent(() => import('../analysis/FigureTab.vue'))
const OutputTab = defineAsyncComponent(() => import('../analysis/OutputTab.vue'))

const tableResultCount = computed(() => Math.max(
  Number(appStore.dataframeCount || 0),
  Array.isArray(appStore.dataframes) ? appStore.dataframes.length : 0,
))
const chartResultCount = computed(() => Math.max(
  Number(appStore.figureCount || 0),
  Array.isArray(appStore.figures) ? appStore.figures.length : 0,
))
const runResultCount = computed(() => buildUserRunItems({
  terminalEntries: appStore.terminalEntries,
  conversationId: appStore.activeConversationId,
}).length)
const resultCategoryOptions = computed(() => [
  { value: 'table', label: 'Tables', icon: TableCellsIcon, count: tableResultCount.value },
  { value: 'chart', label: 'Charts', icon: ChartBarIcon, count: chartResultCount.value },
  { value: 'runs', label: 'Runs', icon: PlayCircleIcon, count: runResultCount.value },
])

function categoryForPane(pane) {
  if (pane === 'table') return 'table'
  if (pane === 'figure') return 'chart'
  return 'runs'
}

function paneForCategory(category) {
  if (category === 'table') return 'table'
  if (category === 'chart') return 'figure'
  return 'output'
}

const selectedCategory = computed({
  get: () => categoryForPane(appStore.dataPane),
  set: (category) => {
    const normalized = ['table', 'chart', 'runs'].includes(category) ? category : 'runs'
    appStore.setDataPane(paneForCategory(normalized))
    const selected = resultCategoryOptions.value.find((option) => option.value === normalized)
    resultAnnouncement.value = selected ? `${selected.label} selected` : ''
  },
})

watch(() => appStore.dataPane, (pane, previousPane) => {
  if (pane === previousPane) return
  const category = categoryForPane(pane)
  const selected = resultCategoryOptions.value.find((option) => option.value === category)
  resultAnnouncement.value = selected ? `${selected.label} available` : ''
})
</script>
