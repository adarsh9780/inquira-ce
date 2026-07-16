<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <AppToolbar aria-label="Results toolbar">
      <template #start>
        <div class="flex min-w-0 items-center gap-2">
          <span class="shrink-0 text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">
            Results
          </span>
          <HeaderDropdown
            v-model="selectedCategory"
            :options="resultCategoryOptions"
            placeholder="Result type"
            aria-label="Select result category"
            max-width-class="w-[9.5rem]"
          />
        </div>
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
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import AppToolbar from '../ui/AppToolbar.vue'
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

const resultCategoryOptions = [
  { value: 'table', label: 'Tables', icon: TableCellsIcon },
  { value: 'chart', label: 'Charts', icon: ChartBarIcon },
  { value: 'runs', label: 'Runs', icon: PlayCircleIcon },
]

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
    const selected = resultCategoryOptions.find((option) => option.value === normalized)
    resultAnnouncement.value = selected ? `${selected.label} selected` : ''
  },
})

watch(() => appStore.dataPane, (pane, previousPane) => {
  if (pane === previousPane) return
  const category = categoryForPane(pane)
  const selected = resultCategoryOptions.find((option) => option.value === category)
  resultAnnouncement.value = selected ? `${selected.label} available` : ''
})
</script>
