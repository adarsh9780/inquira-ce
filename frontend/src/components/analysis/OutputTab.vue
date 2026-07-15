<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && appStore.dataPane === 'output' && selectedResult">
      <div class="flex min-w-0 items-center justify-end gap-2 text-xs" style="color: var(--color-text-muted);">
        <ArrowPathIcon v-if="selectedResult.status === 'running'" class="h-3.5 w-3.5 animate-spin" />
        <CheckCircleIcon v-else-if="selectedResult.status === 'success'" class="h-3.5 w-3.5" style="color: var(--color-success);" />
        <ExclamationTriangleIcon v-else class="h-3.5 w-3.5" style="color: var(--color-danger);" />
        <span>{{ statusLabel }}</span>
        <span v-if="formattedTimestamp" class="tabular-nums">{{ formattedTimestamp }}</span>
      </div>
    </Teleport>

    <p
      v-if="appStore.terminalEntriesTrimmedCount > 0"
      class="px-1 py-1 text-[11px]"
      style="color: var(--color-text-muted);"
    >
      Older run output was trimmed to keep memory usage stable.
    </p>

    <AppEmptyState
      v-if="!selectedResult"
      title="No run output"
      description="Run code that prints a value, returns a scalar, or raises an error."
    />

    <div v-else-if="selectedResult.kind === 'scalar'" class="h-full overflow-auto px-1 py-2 sm:px-3 sm:py-4">
      <div class="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center">
        <p class="text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Scalar result</p>
        <h2 class="mt-2 text-sm font-semibold" style="color: var(--color-text-main);">{{ selectedResult.label }}</h2>
        <pre
          class="mt-4 whitespace-pre-wrap break-words text-[clamp(1rem,2.4vw,1.5rem)] font-mono leading-relaxed"
          style="color: var(--color-text-main);"
        >{{ scalarValue }}</pre>
        <p v-if="scalarType" class="mt-3 text-xs" style="color: var(--color-text-muted);">Type: {{ scalarType }}</p>
      </div>
    </div>

    <div v-else class="h-full overflow-auto px-1 py-2 sm:px-3 sm:py-4">
      <div class="mx-auto w-full max-w-4xl">
        <div class="flex items-start justify-between gap-4 border-b pb-3" style="border-color: color-mix(in srgb, var(--color-border) 82%, transparent);">
          <div class="min-w-0">
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">
              {{ selectedResult.status === 'error' ? 'Execution error' : 'Execution output' }}
            </p>
            <h2 class="mt-1 truncate text-sm font-semibold" style="color: var(--color-text-main);">{{ selectedResult.label }}</h2>
          </div>
          <span v-if="durationLabel" class="shrink-0 text-xs tabular-nums" style="color: var(--color-text-muted);">{{ durationLabel }}</span>
        </div>

        <div v-if="selectedResult.status === 'running'" class="flex min-h-52 items-center justify-center gap-2 text-sm" style="color: var(--color-text-muted);">
          <ArrowPathIcon class="h-4 w-4 animate-spin" />
          Running code…
        </div>

        <template v-else>
          <pre
            v-if="selectedLog.stdout"
            class="mt-4 whitespace-pre-wrap break-words rounded-md px-3 py-2 text-xs font-mono leading-5"
            style="color: var(--color-text-main); background-color: color-mix(in srgb, var(--color-base) 86%, var(--color-surface));"
          >{{ selectedLog.stdout }}</pre>
          <pre
            v-if="selectedLog.stderr"
            class="mt-4 whitespace-pre-wrap break-words rounded-md border px-3 py-2 text-xs font-mono leading-5"
            style="color: var(--color-danger-text); border-color: color-mix(in srgb, var(--color-danger) 70%, var(--color-border)); background-color: color-mix(in srgb, var(--color-danger-bg) 75%, var(--color-base));"
          >{{ selectedLog.stderr }}</pre>
          <div
            v-if="!selectedLog.stdout && !selectedLog.stderr"
            class="flex min-h-52 items-center justify-center text-sm"
            style="color: var(--color-text-muted);"
          >
            Completed with no displayable output.
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { buildUnifiedResultItems } from '../../utils/unifiedResults'
import AppEmptyState from '../ui/AppEmptyState.vue'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  selectedResultId: {
    type: String,
    default: '',
  },
})

const appStore = useAppStore()
const isMounted = ref(false)

onMounted(() => {
  isMounted.value = true
})

const outputResults = computed(() => buildUnifiedResultItems({
  scalars: appStore.scalars,
  terminalEntries: appStore.terminalEntries,
  activeTurnArtifacts: appStore.activeTurnArtifacts,
}).filter((item) => item.kind === 'log' || item.kind === 'scalar'))

const selectedResult = computed(() => (
  outputResults.value.find((item) => item.id === props.selectedResultId) || null
))

const selectedLog = computed(() => {
  if (selectedResult.value?.kind !== 'log') return { stdout: '', stderr: '' }
  const raw = selectedResult.value.raw || {}
  return {
    stdout: String(raw.stdout || ''),
    stderr: String(raw.stderr || ''),
  }
})

function formatValue(value) {
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

const scalarValue = computed(() => {
  const raw = selectedResult.value?.raw || {}
  const value = Object.prototype.hasOwnProperty.call(raw, 'display_value')
    ? raw.display_value
    : (Object.prototype.hasOwnProperty.call(raw, 'value') ? raw.value : raw?.payload?.value)
  return formatValue(value)
})

const scalarType = computed(() => {
  const raw = selectedResult.value?.raw || {}
  return String(raw.result_type || raw.type || '').trim()
})

const statusLabel = computed(() => {
  if (selectedResult.value?.status === 'running') return 'Running'
  if (selectedResult.value?.status === 'error') return 'Failed'
  return 'Complete'
})

const formattedTimestamp = computed(() => {
  const raw = String(selectedResult.value?.createdAt || '').trim()
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
})

const durationLabel = computed(() => {
  const durationMs = Number(selectedResult.value?.raw?.durationMs)
  if (!Number.isFinite(durationMs) || durationMs < 0) return ''
  return `${(durationMs / 1000).toFixed(2)}s`
})
</script>
