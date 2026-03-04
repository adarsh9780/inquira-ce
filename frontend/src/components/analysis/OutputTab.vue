<template>
  <div class="flex h-full flex-col overflow-hidden rounded-lg border" style="background-color: var(--color-base); border-color: var(--color-border);">
    <Teleport to="#workspace-right-pane-toolbar" v-if="isMounted && appStore.dataPane === 'output'">
      <div class="flex items-center justify-end w-full">
        <p class="text-xs hidden sm:block" style="color: var(--color-text-muted);">Execution timeline with logs, table artifacts, and chart artifacts</p>
      </div>
    </Teleport>

    <div class="border-b px-4 py-2.5" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <div class="flex items-center justify-between gap-3">
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
        <div class="text-xs tabular-nums" style="color: var(--color-text-muted);">
          {{ filteredEvents.length }} {{ filteredEvents.length === 1 ? 'event' : 'events' }}
        </div>
      </div>
      <p
        v-if="appStore.terminalEntriesTrimmedCount > 0"
        class="mt-2 text-[11px]"
        style="color: var(--color-text-muted);"
      >
        Older output entries were trimmed to keep memory usage stable.
      </p>
    </div>

    <div class="min-h-0 flex-1 overflow-hidden">
      <div v-if="filteredEvents.length === 0" class="flex h-full items-center justify-center text-center" style="color: var(--color-text-muted);">
        <div>
          <p class="text-sm">No events yet</p>
          <p class="mt-1 text-xs">Run code to see logs, table outputs, and chart outputs.</p>
        </div>
      </div>

      <div v-else class="h-full flex flex-col lg:flex-row">
        <aside
          class="min-h-0 w-full overflow-y-auto border-b lg:w-[46%] lg:border-b-0 lg:border-r"
          style="border-color: color-mix(in srgb, var(--color-border) 80%, transparent);"
        >
          <button
            v-for="event in filteredEvents"
            :key="event.id"
            class="w-full px-4 py-3 text-left transition-colors border-b"
            style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent);"
            :style="selectedEventId === event.id ? selectedTimelineStyle : defaultTimelineStyle"
            @click="selectedEventId = event.id"
          >
            <div class="flex items-center justify-between gap-3 text-[11px] uppercase tracking-wide" style="color: var(--color-text-muted);">
              <span class="font-medium">{{ event.badgeLabel }}</span>
              <span>{{ formatTimestamp(event.createdAt) }}</span>
            </div>
            <p class="mt-1 text-sm font-medium" style="color: var(--color-text-main);">{{ event.title }}</p>
            <p v-if="event.preview" class="mt-1 text-xs break-words" style="color: var(--color-text-muted);">{{ event.preview }}</p>
          </button>
        </aside>

        <section class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          <div v-if="selectedEvent">
            <div class="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wide" style="color: var(--color-text-muted);">
              <span>{{ selectedEvent.badgeLabel }}</span>
              <span>{{ formatTimestamp(selectedEvent.createdAt) }}</span>
            </div>
            <h3 class="text-sm font-semibold" style="color: var(--color-text-main);">{{ selectedEvent.title }}</h3>

            <template v-if="selectedEvent.type === 'log'">
              <pre
                v-if="selectedEvent.stdout"
                class="mt-3 whitespace-pre-wrap break-words rounded-md px-3 py-2 text-xs font-mono leading-5"
                style="color: var(--color-text-main); background-color: color-mix(in srgb, var(--color-surface) 70%, transparent);"
              >{{ selectedEvent.stdout }}</pre>
              <pre
                v-if="selectedEvent.stderr"
                class="mt-2 whitespace-pre-wrap break-words rounded-r-md border-l-2 bg-red-50/55 px-3 py-2 text-xs font-mono leading-5 text-red-700"
                style="border-left-color: color-mix(in srgb, #ef4444 75%, var(--color-border));"
              >{{ selectedEvent.stderr }}</pre>
            </template>

            <template v-else-if="selectedEvent.type === 'table'">
              <div class="mt-3 rounded-md border px-3 py-2 text-xs" style="border-color: var(--color-border); color: var(--color-text-main);">
                <p><strong>Rows:</strong> {{ formatCount(selectedEvent.rowCount) }}</p>
                <p><strong>Columns:</strong> {{ formatCount(selectedEvent.columnCount) }}</p>
                <p v-if="selectedEvent.artifactId"><strong>Artifact ID:</strong> {{ selectedEvent.artifactId }}</p>
              </div>
              <button
                class="mt-3 inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
                style="border-color: var(--color-border); color: var(--color-text-main);"
                @click="openTableInspector(selectedEvent)"
              >
                Open in Table tab
              </button>
            </template>

            <template v-else-if="selectedEvent.type === 'chart'">
              <div class="mt-3 rounded-md border px-3 py-2 text-xs" style="border-color: var(--color-border); color: var(--color-text-main);">
                <p v-if="selectedEvent.artifactId"><strong>Artifact ID:</strong> {{ selectedEvent.artifactId }}</p>
                <p><strong>Status:</strong> Ready to inspect in the chart pane.</p>
              </div>
              <button
                class="mt-3 inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
                style="border-color: var(--color-border); color: var(--color-text-main);"
                @click="openFigureInspector(selectedEvent)"
              >
                Open in Chart tab
              </button>
            </template>
          </div>
          <div v-else class="h-full flex items-center justify-center text-xs text-center" style="color: var(--color-text-muted);">
            Select an event to inspect details.
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'

const appStore = useAppStore()
const isMounted = ref(false)
const activeFilter = ref('all')
const selectedEventId = ref('')

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

const defaultTimelineStyle = 'background-color: transparent;'
const selectedTimelineStyle = 'background-color: color-mix(in srgb, var(--color-surface) 80%, transparent);'

const analysisLogEvents = computed(() => {
  const entries = Array.isArray(appStore.terminalEntries) ? appStore.terminalEntries : []
  return entries
    .filter((entry) => entry?.kind === 'output' && entry?.source === 'analysis')
    .slice()
    .reverse()
    .map((entry, index) => {
      const stdout = String(entry?.stdout || '')
      const stderr = String(entry?.stderr || '')
      const previewSource = stderr || stdout
      const preview = previewSource ? previewSource.slice(0, 180) : ''
      const severity = stderr.trim() ? 'error' : 'log'
      return {
        id: `log:${String(entry?.createdAt || '')}:${index}`,
        type: 'log',
        badgeLabel: severity === 'error' ? 'stderr' : 'stdout',
        title: String(entry?.label || 'Python output'),
        preview,
        stdout,
        stderr,
        createdAt: String(entry?.createdAt || ''),
        sequence: 100000 - index,
        severity,
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
      title: `Table: ${tableName}`,
      preview: `${formatCount(rowCount)} rows, ${formatCount(columnCount)} columns`,
      rowCount,
      columnCount,
      artifactId,
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
      title: `Chart: ${chartName}`,
      preview: 'Interactive chart artifact',
      artifactId,
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
    return timelineEvents.value.filter((event) => event.type === 'log' && event.severity === 'error')
  }
  if (activeFilter.value === 'tables') {
    return timelineEvents.value.filter((event) => event.type === 'table')
  }
  if (activeFilter.value === 'charts') {
    return timelineEvents.value.filter((event) => event.type === 'chart')
  }
  return timelineEvents.value
})

const selectedEvent = computed(() => {
  if (!selectedEventId.value) return filteredEvents.value[0] || null
  return filteredEvents.value.find((event) => event.id === selectedEventId.value) || null
})

watch(filteredEvents, (events) => {
  if (!Array.isArray(events) || events.length === 0) {
    selectedEventId.value = ''
    return
  }
  const exists = events.some((event) => event.id === selectedEventId.value)
  if (!exists) {
    selectedEventId.value = events[0].id
  }
}, { immediate: true })

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
