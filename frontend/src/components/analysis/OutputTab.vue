<template>
  <div class="flex h-full flex-col overflow-hidden">
    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && appStore.dataPane === 'output'">
      <div class="flex min-w-0 w-full items-center justify-end gap-2">
        <div class="mr-auto text-xs tabular-nums" style="color: var(--color-text-muted);">
          {{ filteredEvents.length }} {{ filteredEvents.length === 1 ? 'event' : 'events' }}
        </div>
        <div class="flex min-w-[9rem] flex-1 items-center justify-end gap-2" style="max-width: min(28vw, 11rem);">
          <FunnelIcon class="h-4 w-4 shrink-0" style="color: var(--color-text-muted);" aria-hidden="true" />
          <HeaderDropdown
            v-model="activeFilter"
            :options="filterOptions"
            placeholder="All"
            aria-label="Filter output events"
            max-width-class="w-full"
          />
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
              <div
                v-if="event.preview.hasRows && event.preview.columns.length > 0"
                class="mt-2 overflow-hidden rounded-lg border"
                style="border-color: color-mix(in srgb, var(--color-border) 80%, transparent); background-color: color-mix(in srgb, var(--color-base) 90%, var(--color-surface));"
              >
                <div class="max-h-72 overflow-auto">
                  <table class="w-max min-w-full border-separate border-spacing-0 text-[11px] font-mono leading-5" style="color: var(--color-text-main);">
                    <thead class="sticky top-0 z-10" style="background-color: color-mix(in srgb, var(--color-surface) 92%, var(--color-base));">
                      <tr>
                        <th class="sticky left-0 z-20 border-b border-r px-2 py-1 text-right font-semibold" style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent); background-color: color-mix(in srgb, var(--color-surface) 94%, var(--color-base));">#</th>
                        <th
                          v-for="column in event.preview.columns"
                          :key="column.key"
                          class="border-b border-r px-2 py-1 text-left font-semibold"
                          style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent);"
                        >
                          {{ column.label }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in event.preview.rows" :key="row.key">
                        <th
                          class="sticky left-0 z-10 border-b border-r px-2 py-1 text-right font-medium"
                          :style="row.isEllipsis ? 'font-style: italic;' : ''"
                          style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent); background-color: color-mix(in srgb, var(--color-surface) 94%, var(--color-base));"
                        >
                          {{ row.indexLabel }}
                        </th>
                        <td
                          v-for="cell in row.cells"
                          :key="cell.key"
                          class="max-w-[14rem] border-b border-r px-2 py-1 align-top"
                          :style="cell.isEllipsis ? 'text-align: center; font-style: italic;' : ''"
                          style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent);"
                        >
                          {{ cell.text }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p
                  class="border-t px-3 py-1.5 text-[11px]"
                  style="border-color: color-mix(in srgb, var(--color-border) 70%, transparent); color: var(--color-text-muted);"
                >
                  Showing {{ formatCount(event.preview.visibleRowCount) }} of {{ formatCount(event.rowCount) }} rows and
                  {{ formatCount(event.preview.visibleColumnCount) }} of {{ formatCount(event.columnCount) }} columns.
                </p>
              </div>
              <p
                v-else
                class="mt-2 rounded-md border px-3 py-2 text-[11px]"
                style="border-color: color-mix(in srgb, var(--color-border) 80%, transparent); color: var(--color-text-muted); background-color: color-mix(in srgb, var(--color-base) 90%, var(--color-surface));"
              >
                No row preview captured for this dataframe yet.
              </p>
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
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  FunnelIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const isMounted = ref(false)
const activeFilter = ref('all')
const expandedEventIds = ref([])
const lastAutoOpenedRunId = ref('')
const PREVIEW_HEAD_ROWS = 8
const PREVIEW_TAIL_ROWS = 8
const PREVIEW_HEAD_COLUMNS = 5
const PREVIEW_TAIL_COLUMNS = 4

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
    const preview = buildDataframePreview(item?.data)
    const rowCount = Number(preview.rowCount || 0)
    const columnCount = Number(preview.columnCount || 0)
    const payload = item?.data && typeof item.data === 'object' ? item.data : {}
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
      preview,
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

function normalizeRowsFromDataframeValue(value) {
  if (Array.isArray(value)) {
    return value
      .filter((row) => row && typeof row === 'object' && !Array.isArray(row))
      .map((row) => ({ ...row }))
  }
  if (!value || typeof value !== 'object') return []

  const rawRows = Array.isArray(value.data) ? value.data : []
  if (!rawRows.length) return []
  if (typeof rawRows[0] === 'object' && !Array.isArray(rawRows[0])) {
    return rawRows.map((row) => ({ ...row }))
  }

  const columns = Array.isArray(value.columns) ? value.columns.map((col) => String(col)) : []
  if (!columns.length) return []

  return rawRows.map((row) => {
    if (!Array.isArray(row)) return {}
    const mapped = {}
    columns.forEach((col, idx) => {
      mapped[col] = row[idx]
    })
    return mapped
  })
}

function formatPreviewCell(value) {
  if (value === undefined) return ''
  if (value === null) return 'null'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch (_error) {
    return String(value)
  }
}

function makeVisibleColumns(columns) {
  const normalized = columns.map((column, idx) => ({
    key: `column:${idx}`,
    sourceKey: column,
    label: column,
    isEllipsis: false,
  }))
  const maxColumns = PREVIEW_HEAD_COLUMNS + PREVIEW_TAIL_COLUMNS
  if (normalized.length <= maxColumns) return normalized
  const head = normalized.slice(0, PREVIEW_HEAD_COLUMNS)
  const tail = normalized.slice(-PREVIEW_TAIL_COLUMNS)
  return [
    ...head,
    {
      key: 'column:ellipsis',
      sourceKey: '',
      label: '...',
      isEllipsis: true,
    },
    ...tail,
  ]
}

function rowToPreviewCells(row, visibleColumns, rowIndex) {
  const safeRow = row && typeof row === 'object' ? row : {}
  return visibleColumns.map((column, columnIndex) => {
    if (column.isEllipsis) {
      return {
        key: `cell:${rowIndex}:${columnIndex}:ellipsis`,
        text: '...',
        isEllipsis: true,
      }
    }
    return {
      key: `cell:${rowIndex}:${columnIndex}`,
      text: formatPreviewCell(safeRow[column.sourceKey]),
      isEllipsis: false,
    }
  })
}

function buildDataframePreview(value) {
  const rows = normalizeRowsFromDataframeValue(value)
  const columnsFromPayload = Array.isArray(value?.columns) ? value.columns.map((column) => String(column)) : []
  const columns = columnsFromPayload.length > 0
    ? columnsFromPayload
    : (rows[0] ? Object.keys(rows[0]).map((column) => String(column)) : [])

  const rowCountRaw = Number(value?.row_count)
  const rowCount = Number.isFinite(rowCountRaw) && rowCountRaw > 0 ? rowCountRaw : rows.length
  const columnCount = columns.length
  const visibleColumns = makeVisibleColumns(columns)
  const indexValues = Array.isArray(value?.index) ? value.index : []
  const maxRows = PREVIEW_HEAD_ROWS + PREVIEW_TAIL_ROWS
  const visibleRows = []

  if (rows.length <= maxRows) {
    rows.forEach((row, idx) => {
      visibleRows.push({
        key: `row:${idx}`,
        indexLabel: formatPreviewCell(indexValues[idx] ?? idx),
        cells: rowToPreviewCells(row, visibleColumns, idx),
        isEllipsis: false,
      })
    })
  } else {
    rows.slice(0, PREVIEW_HEAD_ROWS).forEach((row, idx) => {
      visibleRows.push({
        key: `row:${idx}`,
        indexLabel: formatPreviewCell(indexValues[idx] ?? idx),
        cells: rowToPreviewCells(row, visibleColumns, idx),
        isEllipsis: false,
      })
    })
    visibleRows.push({
      key: 'row:ellipsis',
      indexLabel: '...',
      cells: visibleColumns.map((column, index) => ({
        key: `cell:ellipsis:${index}:${column.key}`,
        text: '...',
        isEllipsis: true,
      })),
      isEllipsis: true,
    })
    const tailStart = rows.length - PREVIEW_TAIL_ROWS
    rows.slice(tailStart).forEach((row, offset) => {
      const idx = tailStart + offset
      visibleRows.push({
        key: `row:${idx}`,
        indexLabel: formatPreviewCell(indexValues[idx] ?? idx),
        cells: rowToPreviewCells(row, visibleColumns, idx),
        isEllipsis: false,
      })
    })
  }

  return {
    rows: visibleRows,
    columns: visibleColumns,
    rowCount,
    columnCount,
    hasRows: rows.length > 0,
    visibleRowCount: visibleRows.filter((row) => !row.isEllipsis).length,
    visibleColumnCount: visibleColumns.filter((column) => !column.isEllipsis).length,
  }
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
