<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && appStore.dataPane === 'output'">
      <div class="text-xs tabular-nums" style="color: var(--color-text-muted);">
        {{ executionItems.length }} {{ executionItems.length === 1 ? 'run' : 'runs' }}
      </div>
    </Teleport>

    <p
      v-if="appStore.terminalEntriesTrimmedCount > 0"
      class="shrink-0 px-1 py-1 text-[11px]"
      style="color: var(--color-text-muted);"
    >
      Older runs were trimmed to keep memory usage stable.
    </p>

    <AppEmptyState
      v-if="executionItems.length === 0"
      title="No manual runs yet"
      description="Run code from the editor to see its code, text, tables, and charts together here."
    >
      <template #icon><PlayIcon class="h-7 w-7" /></template>
    </AppEmptyState>

    <div v-else class="min-h-0 flex-1 overflow-y-auto px-1 sm:px-3" data-runs-feed>
      <div class="mx-auto w-full max-w-7xl divide-y" style="border-color: color-mix(in srgb, var(--color-border) 78%, transparent);">
        <article
          v-for="execution in executionItems"
          :key="execution.id"
          class="py-3 first:pt-0 last:pb-8"
          data-user-run
        >
          <button
            type="button"
            class="flex w-full items-center justify-between gap-4 py-2 text-left"
            :aria-expanded="isExpanded(execution.id)"
            @click="toggleRun(execution.id)"
          >
            <span class="flex min-w-0 items-center gap-2.5">
              <ArrowPathIcon v-if="execution.status === 'running'" class="h-4 w-4 shrink-0 animate-spin" style="color: var(--color-text-muted);" />
              <CheckCircleIcon v-else-if="execution.status === 'success'" class="h-4 w-4 shrink-0" style="color: var(--color-success);" />
              <ExclamationTriangleIcon v-else class="h-4 w-4 shrink-0" style="color: var(--color-danger);" />
              <span class="min-w-0">
                <span class="block truncate text-sm font-semibold" style="color: var(--color-text-main);">{{ execution.label }}</span>
                <span class="mt-0.5 block text-[11px]" style="color: var(--color-text-muted);">
                  {{ outputSummary(execution) }}
                </span>
              </span>
            </span>
            <span class="flex shrink-0 items-center gap-3 text-xs tabular-nums" style="color: var(--color-text-muted);">
              <span v-if="formatDuration(execution.durationMs)">{{ formatDuration(execution.durationMs) }}</span>
              <span v-if="formatTimestamp(execution.createdAt)">{{ formatTimestamp(execution.createdAt) }}</span>
              <ChevronDownIcon class="h-4 w-4 transition-transform" :class="isExpanded(execution.id) ? 'rotate-180' : ''" />
            </span>
          </button>

          <div
            v-if="isExpanded(execution.id)"
            class="grid min-w-0 gap-5 pb-4 pt-3 md:grid-cols-[minmax(15rem,0.85fr)_minmax(0,1.15fr)]"
            data-run-body
          >
            <section class="min-w-0 md:border-r md:pr-5" style="border-color: var(--color-border);">
              <p class="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Code</p>
              <pre
                class="max-h-[34rem] overflow-auto whitespace-pre-wrap break-words border-l-2 pl-4 text-xs font-mono leading-5"
                :class="execution.code ? '' : 'italic'"
                :style="execution.code
                  ? 'color: var(--color-text-main); border-color: color-mix(in srgb, var(--color-accent) 55%, var(--color-border));'
                  : 'color: var(--color-text-muted); border-color: var(--color-border);'"
                data-execution-code
              >{{ execution.code || '# Code was not captured for this run.' }}</pre>
            </section>

            <section class="min-w-0">
              <p class="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Output</p>
              <div v-if="execution.status === 'running'" class="flex items-center gap-2 py-1 text-sm" style="color: var(--color-text-muted);">
                <ArrowPathIcon class="h-4 w-4 animate-spin" />
                Running code…
              </div>

              <template v-else>
                <pre v-if="execution.stdout" class="whitespace-pre-wrap break-words text-xs font-mono leading-5" style="color: var(--color-text-main);" data-execution-stdout>{{ execution.stdout }}</pre>
                <pre
                  v-if="execution.stderr"
                  class="whitespace-pre-wrap break-words border-l-2 pl-4 text-xs font-mono leading-5"
                  :class="execution.stdout ? 'mt-4' : ''"
                  style="color: var(--color-danger-text); border-color: var(--color-danger);"
                  data-execution-stderr
                >{{ execution.stderr }}</pre>

                <dl v-if="execution.scalarOutputs.length > 0" class="mt-4 divide-y border-y" style="border-color: var(--color-border);">
                  <div v-for="scalar in execution.scalarOutputs" :key="scalar.id" class="grid gap-2 py-2.5 sm:grid-cols-[minmax(7rem,0.35fr)_minmax(0,1fr)]">
                    <dt class="min-w-0 text-xs font-medium" style="color: var(--color-text-sub);">
                      <span class="break-words">{{ scalar.name }}</span>
                      <span v-if="scalar.type" class="ml-1 font-normal" style="color: var(--color-text-muted);">· {{ scalar.type }}</span>
                    </dt>
                    <dd class="min-w-0"><pre class="whitespace-pre-wrap break-words text-xs font-mono leading-5" style="color: var(--color-text-main);">{{ formatScalarValue(scalar.value) }}</pre></dd>
                  </div>
                </dl>

                <section v-for="(table, index) in execution.tableOutputs" :key="table.id" class="mt-5 border-t pt-4" style="border-color: var(--color-border);">
                  <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h3 class="text-xs font-semibold" style="color: var(--color-text-main);">{{ table.name }}</h3>
                    <button type="button" class="btn-secondary px-2.5 py-1 text-xs" @click="promoteTable(execution, table, index)">
                      {{ tablePromotionLabel }}
                    </button>
                  </div>
                  <RunTableOutput :output="table" />
                </section>

                <section v-for="(chart, index) in execution.chartOutputs" :key="chart.id" class="mt-5 border-t pt-4" style="border-color: var(--color-border);">
                  <div class="mb-1 flex flex-wrap items-center justify-between gap-2">
                    <h3 class="text-xs font-semibold" style="color: var(--color-text-main);">{{ chart.name }}</h3>
                    <button type="button" class="btn-secondary px-2.5 py-1 text-xs" @click="promoteChart(execution, chart, index)">
                      {{ chartPromotionLabel }}
                    </button>
                  </div>
                  <RunChartOutput :output="chart" />
                </section>

                <p v-if="!hasOutput(execution)" class="py-1 text-sm" style="color: var(--color-text-muted);">
                  Completed without output.
                </p>
                <p v-if="execution.truncated" class="mt-3 text-[11px]" style="color: var(--color-text-muted);">Output was truncated by the runtime.</p>
              </template>
            </section>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { buildUserRunItems } from '../../utils/unifiedResults'
import AppEmptyState from '../ui/AppEmptyState.vue'
import RunTableOutput from './runs/RunTableOutput.vue'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  PlayIcon,
} from '@heroicons/vue/24/outline'

const RunChartOutput = defineAsyncComponent(() => import('./runs/RunChartOutput.vue'))
const appStore = useAppStore()
const isMounted = ref(false)
const expandedRunIds = ref(new Set())
let newestRunId = ''

onMounted(() => {
  isMounted.value = true
})

const executionItems = computed(() => buildUserRunItems({
  terminalEntries: appStore.terminalEntries,
  conversationId: appStore.activeConversationId,
}))

watch(executionItems, (items) => {
  const nextNewestId = String(items[0]?.id || '')
  if (!nextNewestId) {
    expandedRunIds.value = new Set()
    newestRunId = ''
    return
  }
  if (nextNewestId !== newestRunId) {
    newestRunId = nextNewestId
    expandedRunIds.value = new Set([nextNewestId])
  }
}, { immediate: true })

const hasAiTables = computed(() => (
  (Array.isArray(appStore.dataframes) && appStore.dataframes.length > 0)
  || (Array.isArray(appStore.activeTurnArtifacts) && appStore.activeTurnArtifacts.some((item) => String(item?.kind || '').toLowerCase() === 'dataframe'))
))
const hasAiCharts = computed(() => (
  (Array.isArray(appStore.figures) && appStore.figures.length > 0)
  || (Array.isArray(appStore.activeTurnArtifacts) && appStore.activeTurnArtifacts.some((item) => String(item?.kind || '').toLowerCase() === 'figure'))
))
const tablePromotionLabel = computed(() => hasAiTables.value ? 'Replace current table' : 'Use as current table')
const chartPromotionLabel = computed(() => hasAiCharts.value ? 'Replace current chart' : 'Use as current chart')

function isExpanded(id) {
  return expandedRunIds.value.has(id)
}

function toggleRun(id) {
  const next = new Set(expandedRunIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedRunIds.value = next
}

function hasOutput(execution) {
  return Boolean(
    execution.stdout
    || execution.stderr
    || execution.scalarOutputs.length
    || execution.tableOutputs.length
    || execution.chartOutputs.length,
  )
}

function outputSummary(execution) {
  if (execution.status === 'running') return 'Running'
  const parts = []
  if (execution.stdout) parts.push('text')
  if (execution.stderr) parts.push('error')
  if (execution.scalarOutputs.length) parts.push(`${execution.scalarOutputs.length} scalar${execution.scalarOutputs.length === 1 ? '' : 's'}`)
  if (execution.tableOutputs.length) parts.push(`${execution.tableOutputs.length} table${execution.tableOutputs.length === 1 ? '' : 's'}`)
  if (execution.chartOutputs.length) parts.push(`${execution.chartOutputs.length} chart${execution.chartOutputs.length === 1 ? '' : 's'}`)
  return parts.length ? parts.join(' · ') : 'No output'
}

function promoteTable(execution, table, index) {
  appStore.promoteUserRunTable(table, { runId: execution.runId, outputId: table.id, index })
}

function promoteChart(execution, chart, index) {
  appStore.promoteUserRunFigure(chart, { runId: execution.runId, outputId: chart.id, index })
}

function formatTimestamp(raw) {
  const value = String(raw || '').trim()
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDuration(durationMs) {
  const value = Number(durationMs)
  if (!Number.isFinite(value) || value < 0) return ''
  return `${(value / 1000).toFixed(2)}s`
}

function formatScalarValue(value) {
  if (value === undefined) return 'Result payload is unavailable.'
  if (value === null) return 'null'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  try {
    return JSON.stringify(value, null, 2)
  } catch (_error) {
    return String(value)
  }
}
</script>
