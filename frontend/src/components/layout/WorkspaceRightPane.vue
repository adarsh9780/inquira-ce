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
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { artifactApi } from '../../api/artifacts'
import { isArtifactAvailable } from '../../utils/artifactAvailability'
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
const workspaceStore = useWorkspaceStore()
const paneRef = ref<HTMLElement | null>(null)
const paneWidth = ref(0)
const resultAnnouncement = ref('')
const catalogTableCount = ref(0)
const catalogChartCount = ref(0)
let paneResizeObserver: ResizeObserver | null = null
let artifactCatalogAbortController: AbortController | null = null
const TableTab = defineAsyncComponent(() => import('../analysis/TableTab.vue'))
const FigureTab = defineAsyncComponent(() => import('../analysis/FigureTab.vue'))
const OutputTab = defineAsyncComponent(() => import('../analysis/OutputTab.vue'))
const toolbarMode = computed<'wide' | 'compact' | 'minimal'>(() => {
  if (paneWidth.value >= 900) return 'wide'
  if (paneWidth.value >= 520) return 'compact'
  return 'minimal'
})

const tableResultCount = computed(() => Math.max(
  catalogTableCount.value,
  Number(artifactStore.dataframeCount || 0),
  Array.isArray(artifactStore.dataframes) ? artifactStore.dataframes.length : 0,
))
const chartResultCount = computed(() => Math.max(
  catalogChartCount.value,
  Number(artifactStore.figureCount || 0),
  Array.isArray(artifactStore.figures) ? artifactStore.figures.length : 0,
))
const runResultCount = computed(() => buildUserRunItems({
  terminalEntries: executionStore.terminalEntries,
  conversationId: conversationStore.activeConversationId,
}).length)
const resultCategoryOptions = computed(() => [
  { value: 'chart', label: 'Charts', icon: ChartBarIcon, count: chartResultCount.value },
  { value: 'table', label: 'Tables', icon: TableCellsIcon, count: tableResultCount.value },
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

watch(chartResultCount, (count, previousCount) => {
  if (count > 0 && count > previousCount) uiStore.setDataPane('figure')
})

function availableArtifactCount(response: any) {
  const artifacts = Array.isArray(response?.artifacts) ? response.artifacts : []
  return artifacts.filter(isArtifactAvailable).length
}

async function refreshResultArtifactCounts() {
  const conversationId = String(conversationStore.activeConversationId || '').trim()
  const turnId = String(conversationStore.activeTurnId || '').trim()
  const workspaceId = String(workspaceStore.activeWorkspaceId || '').trim()
  artifactCatalogAbortController?.abort()
  catalogTableCount.value = 0
  catalogChartCount.value = 0
  if (!workspaceId || !conversationId || !turnId) return

  const controller = new AbortController()
  artifactCatalogAbortController = controller
  try {
    const [tableResponse, chartResponse] = await Promise.all([
      artifactApi.listTurn(conversationId, turnId, 'dataframe', { signal: controller.signal }),
      artifactApi.listTurn(conversationId, turnId, 'figure', { signal: controller.signal }),
    ])
    if (controller.signal.aborted) return
    const tableCount = availableArtifactCount(tableResponse)
    const chartCount = availableArtifactCount(chartResponse)
    catalogTableCount.value = tableCount
    catalogChartCount.value = chartCount
    artifactStore.setDataframeCount(tableCount)
    artifactStore.setFigureCount(chartCount)

    if (chartCount > 0) {
      uiStore.setDataPane('figure')
      resultAnnouncement.value = `${chartCount} chart${chartCount === 1 ? '' : 's'} available`
    } else if (tableCount > 0) {
      uiStore.setDataPane('table')
      resultAnnouncement.value = `${tableCount} table${tableCount === 1 ? '' : 's'} available`
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to discover active turn artifacts:', error)
  }
}

watch(
  () => [
    String(workspaceStore.activeWorkspaceId || '').trim(),
    String(conversationStore.activeConversationId || '').trim(),
    String(conversationStore.activeTurnId || '').trim(),
    String(artifactStore.activeTurnArtifactRefreshKey || 0),
  ].join('||'),
  () => void refreshResultArtifactCounts(),
  { immediate: true },
)

onMounted(() => {
  if (!('ResizeObserver' in window) || !paneRef.value) return
  paneResizeObserver = new ResizeObserver(([entry]) => {
    paneWidth.value = Number(entry?.contentRect?.width || paneRef.value?.clientWidth || 0)
  })
  paneResizeObserver.observe(paneRef.value)
})

onBeforeUnmount(() => {
  artifactCatalogAbortController?.abort()
  paneResizeObserver?.disconnect()
})
</script>
