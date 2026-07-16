<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && appStore.dataPane === 'output'">
      <div class="flex items-center gap-3">
        <button
          v-if="focusedRunId"
          type="button"
          class="flex items-center gap-1.5 text-xs font-medium"
          style="color: var(--color-text-sub);"
          @click="focusedRunId = ''"
        >
          <ArrowLeftIcon class="h-3.5 w-3.5" />
          All runs
        </button>
        <span class="text-xs tabular-nums" style="color: var(--color-text-muted);">
          {{ focusedRunId ? 'Full output' : `${executionItems.length} ${executionItems.length === 1 ? 'run' : 'runs'}` }}
        </span>
      </div>
    </Teleport>

    <p
      v-if="appStore.terminalEntriesTrimmedCount > 0 && !focusedRunId"
      class="shrink-0 px-1 py-1 text-[11px]"
      style="color: var(--color-text-muted);"
    >
      Older runs were trimmed to keep memory usage stable.
    </p>

    <AppEmptyState
      v-if="executionItems.length === 0"
      title="No manual runs yet"
      description="Run code from the editor to see its output here."
    >
      <template #icon><PlayIcon class="h-7 w-7" /></template>
    </AppEmptyState>

    <div v-else class="min-h-0 flex-1 overflow-y-auto px-2 sm:px-4" data-runs-feed>
      <div class="mx-auto w-full max-w-7xl divide-y" style="border-color: color-mix(in srgb, var(--color-border) 78%, transparent);">
        <article
          v-for="execution in visibleExecutionItems"
          :key="execution.id"
          class="py-4 first:pt-1 last:pb-10"
          data-user-run
        >
          <header class="flex min-w-0 items-center gap-2 py-1.5">
            <button
              type="button"
              class="flex min-w-0 flex-1 items-center gap-2.5 text-left"
              :aria-expanded="isRunOpen(execution.id)"
              @click="toggleRun(execution.id)"
            >
              <ArrowPathIcon v-if="execution.status === 'running'" class="h-3.5 w-3.5 shrink-0 animate-spin" style="color: var(--color-text-muted);" />
              <CheckCircleIcon v-else-if="execution.status === 'success'" class="h-3.5 w-3.5 shrink-0" style="color: var(--color-success);" />
              <ExclamationTriangleIcon v-else class="h-3.5 w-3.5 shrink-0" style="color: var(--color-danger);" />
              <span class="min-w-0">
                <span class="block truncate text-xs font-semibold" style="color: var(--color-text-sub);">{{ execution.label }}</span>
                <span class="mt-0.5 block text-[11px]" style="color: var(--color-text-muted);">{{ outputSummary(execution) }}</span>
              </span>
            </button>

            <span class="hidden shrink-0 items-center gap-3 text-[11px] tabular-nums sm:flex" style="color: var(--color-text-muted);">
              <span v-if="formatDuration(execution.durationMs)">{{ formatDuration(execution.durationMs) }}</span>
              <span v-if="formatTimestamp(execution.createdAt)">{{ formatTimestamp(execution.createdAt) }}</span>
            </span>
            <button
              v-if="hasLargeInlineOutput(execution) && focusedRunId !== execution.id"
              type="button"
              class="btn-icon h-7 w-7 shrink-0"
              title="Open full output"
              aria-label="Open full output"
              @click="focusRun(execution.id)"
            >
              <ArrowsPointingOutIcon class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              class="btn-icon h-7 w-7 shrink-0 hover:text-[var(--color-danger)]"
              title="Delete run and release its output from memory"
              aria-label="Delete run"
              @click="deleteRun(execution)"
            >
              <TrashIcon class="h-3.5 w-3.5" />
            </button>
            <button
              v-if="focusedRunId !== execution.id"
              type="button"
              class="btn-icon h-7 w-7 shrink-0"
              :title="isRunOpen(execution.id) ? 'Collapse run' : 'Expand run'"
              :aria-label="isRunOpen(execution.id) ? 'Collapse run' : 'Expand run'"
              @click="toggleRun(execution.id)"
            >
              <ChevronDownIcon class="h-3.5 w-3.5 transition-transform" :class="isRunOpen(execution.id) ? 'rotate-180' : ''" />
            </button>
          </header>

          <div v-if="isRunOpen(execution.id)" class="min-w-0 pb-2 pt-3" data-run-body>
            <pre
              class="max-h-40 overflow-auto whitespace-pre-wrap break-words px-0.5 text-[11px] font-mono leading-4"
              :class="execution.code ? '' : 'italic'"
              style="color: var(--color-text-muted);"
              data-execution-code
            >{{ execution.code || '# Code was not captured for this run.' }}</pre>

            <div class="mt-3 min-w-0 border-t pt-4" style="border-color: var(--color-border);">
              <div v-if="execution.status === 'running'" class="flex items-center gap-2 py-1 text-sm" style="color: var(--color-text-muted);">
                <ArrowPathIcon class="h-4 w-4 animate-spin" />
                Running code…
              </div>

              <template v-else>
                <pre
                  v-if="execution.stdout"
                  class="whitespace-pre-wrap break-words text-xs font-mono leading-5"
                  style="color: var(--color-text-main);"
                  data-execution-stdout
                >{{ displayText(execution.stdout, execution) }}</pre>
                <pre
                  v-if="execution.stderr"
                  class="whitespace-pre-wrap break-words border-l-2 pl-4 text-xs font-mono leading-5"
                  :class="execution.stdout ? 'mt-4' : ''"
                  style="color: var(--color-danger-text); border-color: var(--color-danger);"
                  data-execution-stderr
                >{{ displayText(execution.stderr, execution) }}</pre>

                <pre
                  v-if="execution.scalarOutputs.length > 0"
                  class="whitespace-pre-wrap break-words text-xs font-mono leading-5"
                  :class="(execution.stdout || execution.stderr) ? 'mt-4' : ''"
                  style="color: var(--color-text-main);"
                  data-run-scalar
                >{{ displayScalar(execution.scalarOutputs[0]?.value, execution) }}</pre>

                <section v-if="execution.tableOutputs.length > 0" class="min-w-0" :class="hasTextOutput(execution) ? 'mt-5' : ''">
                  <div class="mb-2 flex justify-end">
                    <button type="button" class="btn-secondary px-2.5 py-1 text-xs" @click="promoteTable(execution, execution.tableOutputs[0], 0)">
                      Open in Tables
                    </button>
                  </div>
                  <RunTableOutput :output="execution.tableOutputs[0]" />
                </section>

                <section v-if="execution.chartOutputs.length > 0" class="min-w-0" :class="hasTextOutput(execution) ? 'mt-5' : ''">
                  <div class="mb-1 flex justify-end">
                    <button type="button" class="btn-secondary px-2.5 py-1 text-xs" @click="promoteChart(execution, execution.chartOutputs[0], 0)">
                      Open in Charts
                    </button>
                  </div>
                  <RunChartOutput :output="execution.chartOutputs[0]" />
                </section>

                <div
                  v-if="hasLargeInlineOutput(execution) && focusedRunId !== execution.id"
                  class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-[11px]"
                  style="border-color: var(--color-border); color: var(--color-text-muted);"
                >
                  <span>Output shortened to keep Runs responsive.</span>
                  <button type="button" class="font-semibold" style="color: var(--color-accent);" @click="focusRun(execution.id)">
                    Open full output
                  </button>
                </div>

                <p v-if="!hasOutput(execution)" class="py-1 text-sm" style="color: var(--color-text-muted);">No output</p>
                <p v-if="execution.truncated" class="mt-3 text-[11px]" style="color: var(--color-text-muted);">Output was truncated by the runtime.</p>
              </template>
            </div>
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
  ArrowLeftIcon,
  ArrowPathIcon,
  ArrowsPointingOutIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'

const INLINE_TEXT_LIMIT = 4_000
const RunChartOutput = defineAsyncComponent(() => import('./runs/RunChartOutput.vue'))
const appStore = useAppStore()
const isMounted = ref(false)
const expandedRunIds = ref(new Set())
const focusedRunId = ref('')
let newestRunId = ''

onMounted(() => {
  isMounted.value = true
})

const executionItems = computed(() => buildUserRunItems({
  terminalEntries: appStore.terminalEntries,
  conversationId: appStore.activeConversationId,
}))

const visibleExecutionItems = computed(() => {
  if (!focusedRunId.value) return executionItems.value
  return executionItems.value.filter((execution) => execution.id === focusedRunId.value)
})

watch(executionItems, (items) => {
  if (focusedRunId.value && !items.some((item) => item.id === focusedRunId.value)) focusedRunId.value = ''
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

function isRunOpen(id) {
  return focusedRunId.value === id || expandedRunIds.value.has(id)
}

function toggleRun(id) {
  if (focusedRunId.value === id) return
  const next = new Set(expandedRunIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedRunIds.value = next
}

function focusRun(id) {
  focusedRunId.value = id
  expandedRunIds.value = new Set([id])
}

function deleteRun(execution) {
  if (!execution?.entryId) return
  appStore.removeTerminalEntry(execution.entryId)
  const next = new Set(expandedRunIds.value)
  next.delete(execution.id)
  expandedRunIds.value = next
  if (focusedRunId.value === execution.id) focusedRunId.value = ''
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

function hasTextOutput(execution) {
  return Boolean(execution.stdout || execution.stderr || execution.scalarOutputs.length)
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

function hasLargeInlineOutput(execution) {
  return (
    String(execution.stdout || '').length > INLINE_TEXT_LIMIT
    || String(execution.stderr || '').length > INLINE_TEXT_LIMIT
    || formatScalarValue(execution.scalarOutputs[0]?.value).length > INLINE_TEXT_LIMIT
  )
}

function displayText(value, execution) {
  const text = String(value || '')
  if (focusedRunId.value === execution.id || text.length <= INLINE_TEXT_LIMIT) return text
  return `${text.slice(0, INLINE_TEXT_LIMIT)}\n…`
}

function displayScalar(value, execution) {
  return displayText(formatScalarValue(value), execution)
}

function outputSummary(execution) {
  if (execution.status === 'running') return 'Running'
  const parts = []
  if (execution.stdout) parts.push('text')
  if (execution.stderr) parts.push('error')
  if (execution.scalarOutputs.length) parts.push('value')
  if (execution.tableOutputs.length) parts.push('table')
  if (execution.chartOutputs.length) parts.push('chart')
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
</script>
