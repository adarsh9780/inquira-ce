<template>
  <div class="flex h-full flex-col overflow-hidden">
    <Teleport to="#workspace-right-pane-toolbar" v-if="isMounted && appStore.dataPane === 'output'">
      <div class="flex w-full items-center gap-3">
        <div class="inline-flex items-center rounded-xl p-0.5" style="background-color: color-mix(in srgb, var(--color-border) 35%, transparent);">
          <button
            v-for="option in filterOptions"
            :key="option.value"
            @click="activeFilter = option.value"
            class="rounded-lg px-2.5 py-1 text-xs transition-colors"
            :class="activeFilter === option.value ? 'bg-white shadow-sm' : ''"
            :style="activeFilter === option.value ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
          >
            {{ option.label }}
          </button>
        </div>
        <div class="ml-auto text-xs tabular-nums" style="color: var(--color-text-muted);">
          {{ filteredEvents.length }} {{ filteredEvents.length === 1 ? 'event' : 'events' }}
        </div>
      </div>
    </Teleport>

    <p
      v-if="appStore.terminalEntriesTrimmedCount > 0"
      class="px-1 py-1 text-[11px]"
      style="color: var(--color-text-muted);"
    >
      Older output entries were trimmed to keep memory usage stable.
    </p>

    <div class="min-h-0 flex-1 overflow-hidden">
      <div v-if="filteredEvents.length === 0" class="flex h-full items-center justify-center text-center" style="color: var(--color-text-muted);">
        <div>
          <p class="text-sm">No events yet</p>
          <p class="mt-1 text-xs">Run code to see logs, table outputs, and chart outputs.</p>
        </div>
      </div>

      <div v-else class="h-full overflow-y-auto pr-1">
        <article
          v-for="event in filteredEvents"
          :key="event.id"
          class="mb-2 overflow-hidden rounded-xl border"
          style="border-color: color-mix(in srgb, var(--color-border) 85%, transparent); background-color: color-mix(in srgb, var(--color-surface) 70%, var(--color-base));"
        >
          <button
            class="flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-black/[0.02]"
            :style="isExpanded(event.id) ? 'background-color: color-mix(in srgb, var(--color-surface) 82%, transparent);' : ''"
            @click="toggleExpanded(event.id)"
          >
            <div class="min-w-0">
              <div class="flex items-center gap-2 text-[11px] uppercase tracking-wide" style="color: var(--color-text-muted);">
                <span class="inline-flex items-center gap-1.5">
                  <ArrowPathIcon v-if="event.status === 'running'" class="h-3.5 w-3.5 animate-spin" style="color: var(--color-text-muted);" />
                  <CheckCircleIcon v-else-if="event.status === 'success'" class="h-3.5 w-3.5" style="color: var(--color-success);" />
                  <ExclamationTriangleIcon v-else-if="event.status === 'error'" class="h-3.5 w-3.5" style="color: #dc2626;" />
                  <span>{{ event.badgeLabel }}</span>
                </span>
                <span>{{ formatTimestamp(event.createdAt) }}</span>
              </div>
              <p class="mt-1 truncate text-sm font-medium" style="color: var(--color-text-main);">{{ event.title }}</p>
              <p v-if="event.meta" class="mt-1 text-xs" style="color: var(--color-text-muted);">{{ event.meta }}</p>
            </div>
            <ChevronDownIcon
              class="h-4 w-4 shrink-0 transition-transform"
              :class="isExpanded(event.id) ? 'rotate-180' : ''"
              style="color: var(--color-text-muted);"
            />
          </button>

          <div v-if="isExpanded(event.id)" class="px-3 pb-3">
            <template v-if="event.type === 'log'">
              <pre
                v-if="event.stdout"
                class="mt-1 whitespace-pre-wrap break-words rounded-md px-3 py-2 text-xs font-mono leading-5"
                style="color: var(--color-text-main); background-color: color-mix(in srgb, var(--color-base) 85%, var(--color-surface));"
              >{{ event.stdout }}</pre>
              <pre
                v-if="event.stderr"
                class="mt-2 whitespace-pre-wrap break-words rounded-md border px-3 py-2 text-xs font-mono leading-5"
                style="color: #b42318; border-color: color-mix(in srgb, #fca5a5 70%, var(--color-border)); background-color: color-mix(in srgb, #fef2f2 75%, var(--color-base));"
              >{{ event.stderr }}</pre>
              <p
                v-if="!event.stdout && !event.stderr"
                class="mt-2 rounded-md px-3 py-2 text-xs"
                style="color: var(--color-text-muted); background-color: color-mix(in srgb, var(--color-base) 85%, var(--color-surface));"
              >
                No output generated.
              </p>
            </template>

            <template v-else-if="event.type === 'table'">
              <div class="mt-1 rounded-md px-3 py-2 text-xs" style="background-color: color-mix(in srgb, var(--color-base) 85%, var(--color-surface)); color: var(--color-text-main);">
                <p>Rows: {{ formatCount(event.rowCount) }}</p>
                <p>Columns: {{ formatCount(event.columnCount) }}</p>
                <p v-if="event.artifactId">Artifact: {{ event.artifactId }}</p>
              </div>
              <button
                class="mt-2 inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
                style="border-color: var(--color-border); color: var(--color-text-main);"
                @click="openTableInspector(event)"
              >
                Open in Table tab
              </button>
            </template>

            <template v-else-if="event.type === 'chart'">
              <div class="mt-1 rounded-md px-3 py-2 text-xs" style="background-color: color-mix(in srgb, var(--color-base) 85%, var(--color-surface)); color: var(--color-text-main);">
                <p v-if="event.artifactId">Artifact: {{ event.artifactId }}</p>
                <p>Ready to inspect in chart pane.</p>
              </div>
              <button
                class="mt-2 inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
                style="border-color: var(--color-border); color: var(--color-text-main);"
                @click="openFigureInspector(event)"
              >
                Open in Chart tab
              </button>
            </template>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const isMounted = ref(false)
const activeFilter = ref('all')
const expandedEventIds = ref([])
const lastAutoOpenedRunId = ref('')

const filterOptions = [
  { value: 'all', label: 'All' },
  { value: 'logs', label: 'Logs' },
  { value: 'errors', label: 'Errors' },
  { value: 'tables', label: 'Tables' },
  { value: 'charts', label: 'Charts' },
]

onMounted(() => {
  isMounted.value = true
})

function normalizeStatus(status, fallback = 'success') {
  const normalized = String(status || '').trim().toLowerCase()
  if (['running', 'success', 'error'].includes(normalized)) return normalized
  return fallback
}

function fallbackRunId(entry, index) {
  const createdAt = String(entry?.createdAt || '').trim()
  if (createdAt) return `legacy-${createdAt.slice(11, 19).replaceAll(':', '')}-${index + 1}`
  return `legacy-${index + 1}`
}

const analysisLogEvents = computed(() => {
  const entries = Array.isArray(appStore.terminalEntries) ? appStore.terminalEntries : []
  return entries
    .filter((entry) => entry?.kind === 'output' && entry?.source === 'analysis')
    .slice()
    .reverse()
    .map((entry, index) => {
      const stdout = String(entry?.stdout || '')
      const stderr = String(entry?.stderr || '')
      const status = normalizeStatus(entry?.status, stderr.trim() ? 'error' : 'success')
      const runId = String(entry?.runId || '').trim() || fallbackRunId(entry, index)
      const durationMs = Number(entry?.durationMs)
      const hasDuration = Number.isFinite(durationMs) && durationMs >= 0
      return {
        id: String(entry?.id || `log:${String(entry?.createdAt || '')}:${index}`),
        type: 'log',
        badgeLabel: status,
        title: `Run ${runId}`,
        meta: hasDuration ? `${(durationMs / 1000).toFixed(2)}s` : '',
        stdout,
        stderr,
        status,
        runId,
        createdAt: String(entry?.createdAt || ''),
        sequence: 100000 - index,
      }
    })
})

const tableEvents = computed(() => {
  const entries = Array.isArray(appStore.dataframes) ? appStore.dataframes : []
  return entries.map((item, index) => {
    const payload = item?.data && typeof item.data === 'object' ? item.data : {}
    const rowCount = Number(payload?.row_count || 0)
    const columnCount = Array.isArray(payload?.columns) ? payload.columns.length : 0
    const artifactId = String(payload?.artifact_id || item?.artifact_id || '').trim()
    const tableName = String(item?.name || item?.logical_name || artifactId || `table_${index + 1}`)
    return {
      id: `table:${artifactId || tableName}:${index}`,
      type: 'table',
      badgeLabel: 'table',
      title: tableName,
      meta: `${formatCount(rowCount)} rows, ${formatCount(columnCount)} columns`,
      rowCount,
      columnCount,
      artifactId,
      status: 'success',
      createdAt: String(item?.createdAt || item?.created_at || payload?.created_at || ''),
      sequence: 50000 - index,
    }
  })
})

const chartEvents = computed(() => {
  const entries = Array.isArray(appStore.figures) ? appStore.figures : []
  return entries.map((item, index) => {
    const artifactId = String(item?.artifact_id || item?.data?.artifact_id || '').trim()
    const chartName = String(item?.name || item?.logical_name || artifactId || `chart_${index + 1}`)
    return {
      id: `chart:${artifactId || chartName}:${index}`,
      type: 'chart',
      badgeLabel: 'chart',
      title: chartName,
      meta: artifactId ? `artifact ${artifactId}` : 'chart artifact',
      artifactId,
      status: 'success',
      createdAt: String(item?.createdAt || item?.created_at || item?.data?.created_at || ''),
      sequence: 40000 - index,
    }
  })
})

const timelineEvents = computed(() => {
  const combined = [
    ...analysisLogEvents.value,
    ...tableEvents.value,
    ...chartEvents.value,
  ]
  combined.sort((left, right) => {
    const leftTs = Date.parse(String(left?.createdAt || ''))
    const rightTs = Date.parse(String(right?.createdAt || ''))
    const leftValid = Number.isFinite(leftTs)
    const rightValid = Number.isFinite(rightTs)
    if (leftValid && rightValid) return rightTs - leftTs
    if (leftValid) return -1
    if (rightValid) return 1
    return Number(right?.sequence || 0) - Number(left?.sequence || 0)
  })
  return combined
})

const filteredEvents = computed(() => {
  if (activeFilter.value === 'logs') {
    return timelineEvents.value.filter((event) => event.type === 'log')
  }
  if (activeFilter.value === 'errors') {
    return timelineEvents.value.filter((event) => event.type === 'log' && event.status === 'error')
  }
  if (activeFilter.value === 'tables') {
    return timelineEvents.value.filter((event) => event.type === 'table')
  }
  if (activeFilter.value === 'charts') {
    return timelineEvents.value.filter((event) => event.type === 'chart')
  }
  return timelineEvents.value
})

watch(filteredEvents, (events) => {
  const visibleIds = new Set(events.map((event) => event.id))
  expandedEventIds.value = expandedEventIds.value.filter((id) => visibleIds.has(id))
  if (events.length > 0 && expandedEventIds.value.length === 0) {
    expandedEventIds.value = [events[0].id]
  }
}, { immediate: true })

watch(analysisLogEvents, (events) => {
  const newest = events[0]
  if (!newest || newest.type !== 'log') return
  const runId = String(newest.runId || '').trim()
  if (!runId || runId === lastAutoOpenedRunId.value) return

  lastAutoOpenedRunId.value = runId
  activeFilter.value = 'all'
  expandedEventIds.value = [
    newest.id,
    ...expandedEventIds.value.filter((id) => id !== newest.id),
  ]
}, { immediate: true })

function isExpanded(eventId) {
  return expandedEventIds.value.includes(eventId)
}

function toggleExpanded(eventId) {
  if (isExpanded(eventId)) {
    expandedEventIds.value = expandedEventIds.value.filter((id) => id !== eventId)
    return
  }
  expandedEventIds.value = [...expandedEventIds.value, eventId]
}

function formatCount(value) {
  const n = Number(value || 0)
  if (!Number.isFinite(n) || n <= 0) return '0'
  return n.toLocaleString()
}

function openTableInspector(event) {
  const artifactId = String(event?.artifactId || '').trim()
  if (artifactId) {
    const rows = Array.isArray(appStore.dataframes) ? appStore.dataframes.slice() : []
    const idx = rows.findIndex((row) => String(row?.data?.artifact_id || row?.artifact_id || '').trim() === artifactId)
    if (idx > 0) {
      const [picked] = rows.splice(idx, 1)
      rows.unshift(picked)
      appStore.setDataframes(rows)
    }
  }
  appStore.setDataPane('table')
}

function openFigureInspector(event) {
  const artifactId = String(event?.artifactId || '').trim()
  if (artifactId) {
    const rows = Array.isArray(appStore.figures) ? appStore.figures.slice() : []
    const idx = rows.findIndex((row) => String(row?.artifact_id || row?.data?.artifact_id || '').trim() === artifactId)
    if (idx > 0) {
      const [picked] = rows.splice(idx, 1)
      rows.unshift(picked)
      appStore.setFigures(rows)
    }
  }
  appStore.setDataPane('figure')
}

function formatTimestamp(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'n/a'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return 'n/a'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>
