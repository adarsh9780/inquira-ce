<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <Teleport
      to="#workspace-right-pane-toolbar-center"
      v-if="isMounted && appStore.dataPane === 'output' && executionItems.length > 0"
    >
      <nav class="flex items-center gap-1" aria-label="Run history navigation" data-run-navigator>
        <button
          type="button"
          class="btn-icon h-7 w-7 shrink-0"
          :disabled="!canGoPrevious"
          :class="canGoPrevious ? '' : 'opacity-40'"
          title="Previous run"
          aria-label="Previous run"
          @click="selectPreviousRun"
        >
          <ChevronLeftIcon class="h-3.5 w-3.5" />
        </button>
        <HeaderDropdown
          v-model="selectedRunId"
          :options="runHistoryOptions"
          :trigger-label="runPositionLabel"
          :dropdown-min-width="248"
          placeholder="Select run"
          aria-label="Select run from history"
          max-width-class="w-[8.5rem]"
        />
        <button
          type="button"
          class="btn-icon h-7 w-7 shrink-0"
          :disabled="!canGoNext"
          :class="canGoNext ? '' : 'opacity-40'"
          title="Next run"
          aria-label="Next run"
          @click="selectNextRun"
        >
          <ChevronRightIcon class="h-3.5 w-3.5" />
        </button>
      </nav>
    </Teleport>

    <Teleport
      to="#workspace-right-pane-toolbar-right"
      v-if="isMounted && appStore.dataPane === 'output' && focusedRunId"
    >
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="flex items-center gap-1.5 text-xs font-medium"
          style="color: var(--color-text-sub);"
          aria-label="Preview output"
          @click="focusedRunId = ''"
        >
          <ArrowsPointingInIcon class="h-3.5 w-3.5" />
          Preview
        </button>
        <span class="text-xs" style="color: var(--color-text-muted);">Full output</span>
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
      <article
        v-if="selectedExecution"
        :key="selectedExecution.id"
        class="mx-auto w-full max-w-7xl pb-10 pt-1"
        :data-selected-run-id="selectedExecution.id"
        data-user-run
      >
        <header class="flex min-w-0 items-center gap-2 py-1.5">
          <div class="flex min-w-0 flex-1 items-center gap-2.5">
            <ArrowPathIcon
              v-if="selectedExecution.status === 'running'"
              class="h-3.5 w-3.5 shrink-0 animate-spin"
              style="color: var(--color-text-muted);"
            />
            <CheckCircleIcon
              v-else-if="selectedExecution.status === 'success'"
              class="h-3.5 w-3.5 shrink-0"
              style="color: var(--color-success);"
            />
            <ExclamationTriangleIcon
              v-else
              class="h-3.5 w-3.5 shrink-0"
              style="color: var(--color-danger);"
            />
            <span class="min-w-0">
              <span class="block truncate text-xs font-semibold" style="color: var(--color-text-sub);">{{ selectedExecution.label }}</span>
              <span class="mt-0.5 block text-[11px]" style="color: var(--color-text-muted);">{{ outputSummary(selectedExecution) }}</span>
            </span>
          </div>

          <span class="hidden shrink-0 items-center gap-3 text-[11px] tabular-nums sm:flex" style="color: var(--color-text-muted);">
            <span v-if="formatDuration(selectedExecution.durationMs)">{{ formatDuration(selectedExecution.durationMs) }}</span>
            <span v-if="formatTimestamp(selectedExecution.createdAt)">{{ formatTimestamp(selectedExecution.createdAt) }}</span>
          </span>
          <button
            v-if="hasLargeInlineOutput(selectedExecution) && focusedRunId !== selectedExecution.id"
            type="button"
            class="btn-icon h-7 w-7 shrink-0"
            title="Open full output"
            aria-label="Open full output"
            @click="focusRun(selectedExecution.id)"
          >
            <ArrowsPointingOutIcon class="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            class="btn-icon h-7 w-7 shrink-0 hover:text-[var(--color-danger)]"
            title="Delete run and release its output from memory"
            aria-label="Delete run"
            @click="deleteRun(selectedExecution)"
          >
            <TrashIcon class="h-3.5 w-3.5" />
          </button>
        </header>

        <div class="min-w-0 pb-2 pt-3" data-run-body>
          <div class="min-w-0">
            <div v-if="selectedExecution.status === 'running'" class="flex items-center gap-2 py-1 text-sm" style="color: var(--color-text-muted);">
              <ArrowPathIcon class="h-4 w-4 animate-spin" />
              Running code…
            </div>

            <template v-else>
              <pre
                v-if="selectedExecution.stdout"
                class="whitespace-pre-wrap break-words text-xs font-mono leading-5"
                style="color: var(--color-text-main);"
                data-execution-stdout
              >{{ displayText(selectedExecution.stdout, selectedExecution) }}</pre>
              <pre
                v-if="selectedExecution.stderr"
                class="whitespace-pre-wrap break-words border-l-2 pl-4 text-xs font-mono leading-5"
                :class="selectedExecution.stdout ? 'mt-4' : ''"
                style="color: var(--color-danger-text); border-color: var(--color-danger);"
                data-execution-stderr
              >{{ displayText(selectedExecution.stderr, selectedExecution) }}</pre>

              <pre
                v-if="selectedExecution.scalarOutputs.length > 0"
                class="whitespace-pre-wrap break-words text-xs font-mono leading-5"
                :class="(selectedExecution.stdout || selectedExecution.stderr) ? 'mt-4' : ''"
                style="color: var(--color-text-main);"
                data-run-scalar
              >{{ displayScalar(selectedExecution.scalarOutputs[0]?.value, selectedExecution) }}</pre>

              <section
                v-if="selectedExecution.tableOutputs.length > 0"
                class="min-w-0"
                :class="hasTextOutput(selectedExecution) ? 'mt-5' : ''"
              >
                <div class="mb-2 flex justify-end">
                  <button
                    type="button"
                    class="btn-secondary px-2.5 py-1 text-xs"
                    @click="promoteTable(selectedExecution, selectedExecution.tableOutputs[0], 0)"
                  >
                    Open in Tables
                  </button>
                </div>
                <RunTableOutput :output="selectedExecution.tableOutputs[0]" />
              </section>

              <section
                v-if="selectedExecution.chartOutputs.length > 0"
                class="min-w-0"
                :class="hasTextOutput(selectedExecution) ? 'mt-5' : ''"
              >
                <div class="mb-1 flex justify-end">
                  <button
                    type="button"
                    class="btn-secondary px-2.5 py-1 text-xs"
                    @click="promoteChart(selectedExecution, selectedExecution.chartOutputs[0], 0)"
                  >
                    Open in Charts
                  </button>
                </div>
                <RunChartOutput :output="selectedExecution.chartOutputs[0]" />
              </section>

              <div
                v-if="hasLargeInlineOutput(selectedExecution) && focusedRunId !== selectedExecution.id"
                class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-[11px]"
                style="border-color: var(--color-border); color: var(--color-text-muted);"
              >
                <span>Output shortened to keep Runs responsive.</span>
                <button
                  type="button"
                  class="font-semibold"
                  style="color: var(--color-accent);"
                  @click="focusRun(selectedExecution.id)"
                >
                  Open full output
                </button>
              </div>

              <p v-if="!hasOutput(selectedExecution)" class="py-1 text-sm" style="color: var(--color-text-muted);">No output</p>
              <p v-if="selectedExecution.truncated" class="mt-3 text-[11px]" style="color: var(--color-text-muted);">Output was truncated by the runtime.</p>
            </template>
          </div>
          <details class="mt-5 border-t pt-3 text-xs" style="border-color: var(--color-border);">
            <summary class="cursor-pointer select-none font-medium text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)]">
              View source code
            </summary>
            <pre
              class="mt-3 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-[var(--color-surface-inset)] p-3 text-[11px] font-mono leading-4"
              :class="selectedExecution.code ? '' : 'italic'"
              style="color: var(--color-text-muted);"
              data-execution-code
            >{{ selectedExecution.code || '# Code was not captured for this run.' }}</pre>
          </details>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { buildUserRunItems } from '../../utils/unifiedResults'
import AppEmptyState from '../ui/AppEmptyState.vue'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import RunTableOutput from './runs/RunTableOutput.vue'
import {
  ArrowPathIcon,
  ArrowsPointingInIcon,
  ArrowsPointingOutIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'

const INLINE_TEXT_LIMIT = 4_000
const RunChartOutput = defineAsyncComponent(() => import('./runs/RunChartOutput.vue'))
const appStore = useAppStore()
const isMounted = ref(false)
const selectedRunId = ref('')
const focusedRunId = ref('')
let newestRunId = ''

onMounted(() => {
  isMounted.value = true
})

const executionItems = computed(() => buildUserRunItems({
  terminalEntries: appStore.terminalEntries,
  conversationId: appStore.activeConversationId,
}))

const selectedRunIndex = computed(() => (
  executionItems.value.findIndex((execution) => execution.id === selectedRunId.value)
))

const selectedExecution = computed(() => (
  selectedRunIndex.value >= 0 ? executionItems.value[selectedRunIndex.value] : null
))

const runPositionLabel = computed(() => {
  const total = executionItems.value.length
  if (!total || selectedRunIndex.value < 0) return 'Select run'
  return `Run ${total - selectedRunIndex.value} of ${total}`
})

const runHistoryOptions = computed(() => {
  const total = executionItems.value.length
  return executionItems.value.map((execution, index) => ({
    value: execution.id,
    label: [
      `Run ${total - index}`,
      historySummary(execution),
      formatTimestamp(execution.createdAt),
    ].filter(Boolean).join(' · '),
  }))
})

const canGoPrevious = computed(() => (
  selectedRunIndex.value >= 0 && selectedRunIndex.value < executionItems.value.length - 1
))

const canGoNext = computed(() => selectedRunIndex.value > 0)

watch(executionItems, (items) => {
  const nextNewestId = String(items[0]?.id || '')
  if (!nextNewestId) {
    newestRunId = ''
    selectedRunId.value = ''
    focusedRunId.value = ''
    return
  }
  if (nextNewestId !== newestRunId) {
    newestRunId = nextNewestId
    selectedRunId.value = nextNewestId
    return
  }
  if (!items.some((item) => item.id === selectedRunId.value)) {
    selectedRunId.value = nextNewestId
  }
}, { immediate: true })

watch(selectedRunId, () => {
  focusedRunId.value = ''
})

function selectPreviousRun() {
  if (!canGoPrevious.value) return
  selectedRunId.value = executionItems.value[selectedRunIndex.value + 1]?.id || selectedRunId.value
}

function selectNextRun() {
  if (!canGoNext.value) return
  selectedRunId.value = executionItems.value[selectedRunIndex.value - 1]?.id || selectedRunId.value
}

function focusRun(id) {
  focusedRunId.value = id
}

function deleteRun(execution) {
  if (!execution?.entryId) return
  const currentIndex = executionItems.value.findIndex((item) => item.id === execution.id)
  const fallback = executionItems.value[currentIndex - 1] || executionItems.value[currentIndex + 1] || null
  selectedRunId.value = fallback?.id || ''
  appStore.removeTerminalEntry(execution.entryId)
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

function historySummary(execution) {
  if (execution.status === 'running') return 'Running'
  if (execution.status === 'error' || execution.stderr) return 'Error'
  if (execution.chartOutputs.length) return 'Chart'
  if (execution.tableOutputs.length) return 'Table'
  if (execution.scalarOutputs.length) return 'Value'
  if (execution.stdout) return 'Text'
  return 'No output'
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
