<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <AppToolbar aria-label="Results toolbar">
      <template #start>
        <div class="flex min-w-0 items-center gap-2">
          <span class="shrink-0 text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">
            Results
          </span>
          <HeaderDropdown
            v-if="resultOptions.length > 0"
            v-model="selectedResultId"
            :options="resultOptions"
            placeholder="Select result"
            aria-label="Select result"
            max-width-class="w-[clamp(11rem,28vw,20rem)]"
            :searchable="resultOptions.length > 10"
            search-placeholder="Search results"
          />
        </div>
      </template>

      <div id="workspace-right-pane-toolbar-center" class="min-w-0"></div>

      <template #end>
        <div id="workspace-right-pane-toolbar-right" class="min-w-0"></div>
      </template>
    </AppToolbar>

    <p class="sr-only" aria-live="polite">{{ resultAnnouncement }}</p>

    <div class="flex min-h-0 flex-1 flex-col p-2.5 pb-0 sm:p-3 sm:pb-0" style="background-color: var(--color-workspace-surface);">
      <div class="min-h-0 flex-1 overflow-hidden">
        <TableTab v-if="selectedResult?.kind === 'table'" />
        <FigureTab v-else-if="selectedResult?.kind === 'chart'" />
        <OutputTab
          v-else-if="selectedResult?.kind === 'log' || selectedResult?.kind === 'scalar'"
          :selected-result-id="selectedResult.id"
        />
        <AppEmptyState
          v-else
          title="No results yet"
          description="Run code to see tables, charts, values, and execution output here."
        />
      </div>

      <div
        v-if="relatedExecutionLog"
        class="mt-2 shrink-0 border-t"
        style="border-color: color-mix(in srgb, var(--color-border) 82%, transparent);"
      >
        <button
          type="button"
          class="flex h-8 w-full items-center justify-between gap-3 text-left text-xs transition-colors hover:text-[var(--color-text-main)]"
          style="color: var(--color-text-muted);"
          :aria-expanded="executionDetailsOpen"
          @click="executionDetailsOpen = !executionDetailsOpen"
        >
          <span class="inline-flex min-w-0 items-center gap-2">
            <CommandLineIcon class="h-3.5 w-3.5 shrink-0" />
            <span class="truncate">Execution log</span>
            <span class="tabular-nums">{{ relatedExecutionLineCount }} {{ relatedExecutionLineCount === 1 ? 'line' : 'lines' }}</span>
          </span>
          <ChevronDownIcon class="h-4 w-4 shrink-0 transition-transform" :class="executionDetailsOpen ? 'rotate-180' : ''" />
        </button>

        <Transition name="motion-disclosure">
          <div v-if="executionDetailsOpen" class="max-h-40 overflow-auto pb-2">
            <pre
              v-if="relatedExecutionLog.stdout"
              class="whitespace-pre-wrap break-words rounded-md px-3 py-2 text-xs font-mono leading-5"
              style="color: var(--color-text-main); background-color: color-mix(in srgb, var(--color-base) 86%, var(--color-surface));"
            >{{ relatedExecutionLog.stdout }}</pre>
            <pre
              v-if="relatedExecutionLog.stderr"
              class="mt-2 whitespace-pre-wrap break-words rounded-md border px-3 py-2 text-xs font-mono leading-5"
              style="color: var(--color-danger-text); border-color: color-mix(in srgb, var(--color-danger) 70%, var(--color-border)); background-color: color-mix(in srgb, var(--color-danger-bg) 75%, var(--color-base));"
            >{{ relatedExecutionLog.stderr }}</pre>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import {
  buildUnifiedResultItems,
  resultPaneForKind,
} from '../../utils/unifiedResults'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import AppToolbar from '../ui/AppToolbar.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'
import { ChevronDownIcon, CommandLineIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const resultAnnouncement = ref('')
const executionDetailsOpen = ref(false)
const TableTab = defineAsyncComponent(() => import('../analysis/TableTab.vue'))
const FigureTab = defineAsyncComponent(() => import('../analysis/FigureTab.vue'))
const OutputTab = defineAsyncComponent(() => import('../analysis/OutputTab.vue'))

const resultItems = computed(() => buildUnifiedResultItems({
  dataframes: appStore.dataframes,
  figures: appStore.figures,
  scalars: appStore.scalars,
  terminalEntries: appStore.terminalEntries,
  activeTurnArtifacts: appStore.activeTurnArtifacts,
}))

const resultOptions = computed(() => resultItems.value.map((item) => ({
  value: item.id,
  label: item.status === 'running' ? `${item.optionLabel} · Running` : item.optionLabel,
  tags: [item.kind, item.status, item.runId].filter(Boolean),
})))

const selectedResult = computed(() => (
  resultItems.value.find((item) => item.id === appStore.selectedResultId) || null
))

function applyResultSelection(resultId) {
  const normalizedResultId = String(resultId || '').trim()
  const result = resultItems.value.find((item) => item.id === normalizedResultId)
  if (!result) return false

  appStore.setSelectedResultId(result.id)
  appStore.setDataPane(resultPaneForKind(result.kind))
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (workspaceId && result.kind === 'table') {
    appStore.setSelectedTableArtifact(workspaceId, result.artifactId)
  }
  if (workspaceId && result.kind === 'chart') {
    appStore.setSelectedFigureArtifact(workspaceId, result.artifactId)
  }
  return true
}

const selectedResultId = computed({
  get: () => appStore.selectedResultId,
  set: (resultId) => {
    if (applyResultSelection(resultId)) {
      const selected = resultItems.value.find((item) => item.id === resultId)
      resultAnnouncement.value = selected ? `${selected.optionLabel} selected` : ''
    }
  },
})

function paneKinds(pane) {
  if (pane === 'table') return ['table']
  if (pane === 'figure') return ['chart']
  return ['log', 'scalar']
}

function chooseResultForCurrentPane(items) {
  const desiredKinds = paneKinds(appStore.dataPane)
  return items.find((item) => desiredKinds.includes(item.kind)) || items[0] || null
}

watch(resultItems, (items, previousItems) => {
  if (items.some((item) => item.id === appStore.selectedResultId)) return
  const next = chooseResultForCurrentPane(items)
  if (next) applyResultSelection(next.id)
  else appStore.setSelectedResultId('')

  if (items.length > (Array.isArray(previousItems) ? previousItems.length : 0) && next) {
    resultAnnouncement.value = `${next.optionLabel} available`
  }
}, { immediate: true })

watch(() => appStore.dataPane, (pane) => {
  const current = selectedResult.value
  if (current && paneKinds(pane).includes(current.kind)) return
  const next = resultItems.value.find((item) => paneKinds(pane).includes(item.kind))
  if (next) applyResultSelection(next.id)
})

watch(() => appStore.selectedResultId, () => {
  executionDetailsOpen.value = false
})

const relatedExecutionLog = computed(() => {
  const selected = selectedResult.value
  if (!selected || selected.kind === 'log' || !selected.runId) return null
  return (Array.isArray(appStore.terminalEntries) ? appStore.terminalEntries : [])
    .slice()
    .reverse()
    .find((entry) => (
      entry?.kind === 'output'
      && entry?.source === 'analysis'
      && String(entry?.runId || '').trim() === selected.runId
      && (String(entry?.stdout || '').trim() || String(entry?.stderr || '').trim())
    )) || null
})

const relatedExecutionLineCount = computed(() => {
  const entry = relatedExecutionLog.value
  if (!entry) return 0
  return [entry.stdout, entry.stderr]
    .filter((value) => String(value || '').trim())
    .join('\n')
    .split(/\r?\n/)
    .length
})
</script>
