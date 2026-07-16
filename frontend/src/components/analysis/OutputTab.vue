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
      Older run output was trimmed to keep memory usage stable.
    </p>

    <AppEmptyState
      v-if="executionItems.length === 0"
      title="No other output"
      description="Printed values, scalar results, and errors will appear here with the code that produced them."
    >
      <template #icon><CommandLineIcon class="h-7 w-7" /></template>
    </AppEmptyState>

    <div v-else class="min-h-0 flex-1 overflow-y-auto px-1 sm:px-3" data-other-output-feed>
      <div class="mx-auto w-full max-w-5xl divide-y" style="border-color: color-mix(in srgb, var(--color-border) 78%, transparent);">
        <article
          v-for="execution in executionItems"
          :key="execution.id"
          class="py-5 first:pt-2 last:pb-8"
          data-execution-output
        >
          <header class="flex flex-wrap items-start justify-between gap-x-5 gap-y-2">
            <div class="flex min-w-0 items-center gap-2.5">
              <ArrowPathIcon
                v-if="execution.status === 'running'"
                class="h-4 w-4 shrink-0 animate-spin"
                style="color: var(--color-text-muted);"
              />
              <CheckCircleIcon
                v-else-if="execution.status === 'success'"
                class="h-4 w-4 shrink-0"
                style="color: var(--color-success);"
              />
              <ExclamationTriangleIcon
                v-else
                class="h-4 w-4 shrink-0"
                style="color: var(--color-danger);"
              />
              <div class="min-w-0">
                <h2 class="truncate text-sm font-semibold" style="color: var(--color-text-main);">{{ execution.label }}</h2>
                <p class="mt-0.5 text-[11px] uppercase tracking-[0.06em]" style="color: var(--color-text-muted);">
                  {{ statusLabel(execution.status) }}
                </p>
              </div>
            </div>
            <p class="flex shrink-0 items-center gap-2 text-xs tabular-nums" style="color: var(--color-text-muted);">
              <span v-if="formatDuration(execution.durationMs)">{{ formatDuration(execution.durationMs) }}</span>
              <span v-if="formatTimestamp(execution.createdAt)">{{ formatTimestamp(execution.createdAt) }}</span>
            </p>
          </header>

          <div class="mt-4 grid gap-x-5 gap-y-2 md:grid-cols-[4.5rem_minmax(0,1fr)]">
            <p class="pt-0.5 text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Code</p>
            <pre
              class="max-h-64 overflow-auto whitespace-pre-wrap break-words border-l-2 pl-4 text-xs font-mono leading-5"
              :class="execution.code ? '' : 'italic'"
              :style="execution.code
                ? 'color: var(--color-text-main); border-color: color-mix(in srgb, var(--color-accent) 55%, var(--color-border));'
                : 'color: var(--color-text-muted); border-color: var(--color-border);'"
              data-execution-code
            >{{ execution.code || '# Code was not captured for this run.' }}</pre>
          </div>

          <div class="mt-5 grid gap-x-5 gap-y-2 md:grid-cols-[4.5rem_minmax(0,1fr)]">
            <p class="pt-0.5 text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Output</p>
            <div class="min-w-0">
              <div
                v-if="execution.status === 'running'"
                class="flex items-center gap-2 py-1 text-sm"
                style="color: var(--color-text-muted);"
              >
                <ArrowPathIcon class="h-4 w-4 animate-spin" />
                Running code…
              </div>

              <template v-else>
                <pre
                  v-if="execution.stdout"
                  class="whitespace-pre-wrap break-words text-xs font-mono leading-5"
                  style="color: var(--color-text-main);"
                  data-execution-stdout
                >{{ execution.stdout }}</pre>
                <pre
                  v-if="execution.stderr"
                  class="whitespace-pre-wrap break-words border-l-2 pl-4 text-xs font-mono leading-5"
                  :class="execution.stdout ? 'mt-4' : ''"
                  style="color: var(--color-danger-text); border-color: var(--color-danger);"
                  data-execution-stderr
                >{{ execution.stderr }}</pre>

                <dl
                  v-if="execution.scalarOutputs.length > 0"
                  class="divide-y border-y"
                  :class="(execution.stdout || execution.stderr) ? 'mt-4' : ''"
                  style="border-color: color-mix(in srgb, var(--color-border) 78%, transparent);"
                >
                  <div
                    v-for="scalar in execution.scalarOutputs"
                    :key="scalar.id"
                    class="grid gap-2 py-2.5 sm:grid-cols-[minmax(7rem,0.35fr)_minmax(0,1fr)]"
                  >
                    <dt class="min-w-0 text-xs font-medium" style="color: var(--color-text-sub);">
                      <span class="break-words">{{ scalar.name }}</span>
                      <span v-if="scalar.type" class="ml-1 font-normal" style="color: var(--color-text-muted);">· {{ scalar.type }}</span>
                    </dt>
                    <dd class="min-w-0">
                      <pre class="whitespace-pre-wrap break-words text-xs font-mono leading-5" style="color: var(--color-text-main);">{{ formatScalarValue(scalar.value) }}</pre>
                    </dd>
                  </div>
                </dl>

                <p
                  v-if="!execution.stdout && !execution.stderr && execution.scalarOutputs.length === 0"
                  class="py-1 text-sm"
                  style="color: var(--color-text-muted);"
                >
                  Completed without text or scalar output.
                </p>
                <p v-if="execution.truncated" class="mt-3 text-[11px]" style="color: var(--color-text-muted);">
                  Output was truncated by the runtime.
                </p>
              </template>
            </div>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { buildOtherExecutionItems } from '../../utils/unifiedResults'
import AppEmptyState from '../ui/AppEmptyState.vue'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CommandLineIcon,
  ExclamationTriangleIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const isMounted = ref(false)

onMounted(() => {
  isMounted.value = true
})

const executionItems = computed(() => buildOtherExecutionItems({
  terminalEntries: appStore.terminalEntries,
  scalars: appStore.scalars,
  dataframes: appStore.dataframes,
  figures: appStore.figures,
  activeTurnArtifacts: appStore.activeTurnArtifacts,
  fallbackCode: appStore.activeTurnCode,
}))

function statusLabel(status) {
  if (status === 'running') return 'Running'
  if (status === 'error') return 'Failed'
  return 'Complete'
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
