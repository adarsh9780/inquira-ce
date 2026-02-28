<template>
  <div class="flex flex-col h-full">
    <!-- Table Header -->
    <div class="flex-shrink-0 bg-gray-50 border-b border-gray-200 px-4 py-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <h3 class="text-sm font-medium text-gray-900">Data Table</h3>
          <span v-if="appStore.isCodeRunning" class="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
            Processing
          </span>
          <span v-else-if="rowCount > 0" class="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
            {{ rowCount.toLocaleString() }} rows
          </span>
        </div>

        <div class="flex items-center space-x-2">
          <div v-if="selectedDataframeMeta?.artifact_id" class="flex items-center space-x-2 text-xs text-gray-600">
            <span>
              Showing {{ chunkStart.toLocaleString() }}-{{ chunkEnd.toLocaleString() }}
              of {{ rowCount.toLocaleString() }}
            </span>
            <button
              @click="loadPreviousChunk"
              :disabled="chunkOffset === 0 || isChunkLoading"
              class="px-2 py-1 border border-gray-300 rounded bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Prev
            </button>
            <button
              @click="loadNextChunk"
              :disabled="!canLoadNextChunk || isChunkLoading"
              class="px-2 py-1 border border-gray-300 rounded bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>

          <!-- Dataframe Selector -->
          <div v-if="orderedDataframes && orderedDataframes.length > 1" class="flex items-center space-x-2">
            <label for="dataframe-select" class="text-sm font-medium text-gray-700">Dataframe:</label>
            <select
              id="dataframe-select"
              v-model="selectedDataframeIndex"
              class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option
                v-for="(df, index) in orderedDataframes"
                :key="index"
                :value="index"
              >
                {{ df.name }}
              </option>
            </select>
          </div>

          <!-- Download CSV Button -->
          <button
            @click="downloadCsv"
            :disabled="!rowData.length || isDownloading"
            class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!rowData.length ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <ArrowDownTrayIcon v-if="!isDownloading" class="h-4 w-4 mr-1" />
            <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1"></div>
            {{ isDownloading ? 'Downloading...' : 'Download CSV' }}
          </button>
        </div>
      </div>
    </div>

    <!-- AG Grid Container -->
    <div class="flex-1 relative">
      <ag-grid-vue
        v-if="rowData.length"
        :key="`${selectedDataframeIndex}-${chunkOffset}`"
        class="ag-theme-quartz absolute inset-0"
        :columnDefs="columnDefs"
        :rowData="rowData"
        :defaultColDef="defaultColDef"
        :enableClipboard="true"
        :pagination="true"
        :paginationPageSize="100"
        :suppressMenuHide="true"
        :animateRows="true"
        :rowSelection="rowSelection"
        @grid-ready="onGridReady"
      ></ag-grid-vue>

      <!-- Empty State -->
      <div
        v-else
        class="absolute inset-0 flex items-center justify-center bg-gray-50"
      >
        <div class="text-center">
          <TableCellsIcon class="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p class="text-sm text-gray-500">No data to display</p>
          <p class="text-xs text-gray-400 mt-1">Run code to generate table data</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-theme-quartz.css'

// Register AG Grid Community modules
ModuleRegistry.registerModules([AllCommunityModule])
import {
  ArrowDownTrayIcon,
  TableCellsIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const isDownloading = ref(false)
const isChunkLoading = ref(false)
const selectedDataframeIndex = ref(0)
const chunkOffset = ref(0)
const chunkLimit = 1000
const chunkRows = ref([])
let gridApi = null

const orderedDataframes = computed(() => {
  if (!appStore.dataframes) return []
  // latest first
  return [...appStore.dataframes].slice().reverse()
})

const selectedDataframeMeta = computed(() => {
  if (!orderedDataframes.value || orderedDataframes.value.length === 0) return null
  const df = orderedDataframes.value[selectedDataframeIndex.value]
  if (!df || !df.data) return null
  return df.data
})

const rowData = computed(() => {
  const meta = selectedDataframeMeta.value
  if (!meta) return []
  if (meta.artifact_id) return chunkRows.value
  if (Array.isArray(meta)) return meta
  if (Array.isArray(meta.data)) return meta.data
  return []
})

const rowCount = computed(() => {
  const meta = selectedDataframeMeta.value
  if (!meta) return 0
  if (typeof meta.row_count === 'number') return meta.row_count
  if (Array.isArray(meta.data)) return meta.data.length
  if (Array.isArray(meta)) return meta.length
  return rowData.value.length
})

const chunkStart = computed(() => (rowData.value.length ? chunkOffset.value + 1 : 0))
const chunkEnd = computed(() => chunkOffset.value + rowData.value.length)
const canLoadNextChunk = computed(() => chunkEnd.value < rowCount.value)

const columnDefs = computed(() => {
  if (!rowData.value || rowData.value.length === 0) return []
  return generateColumnDefs(rowData.value)
})

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  minWidth: 120
}

const rowSelection = {
  mode: 'multiRow',
  enableClickSelection: true
}

watch(
  () => appStore.dataframes,
  async (newDataframes) => {
    if (newDataframes && newDataframes.length > 0) {
      selectedDataframeIndex.value = 0
      chunkOffset.value = 0
      await refreshSelectedDataframe()
    } else {
      chunkRows.value = []
    }
  },
  { immediate: true },
)

watch(selectedDataframeIndex, async () => {
  chunkOffset.value = 0
  await refreshSelectedDataframe()
})

function onGridReady(params) {
  gridApi = params.api
}

async function refreshSelectedDataframe() {
  const meta = selectedDataframeMeta.value
  if (!meta || !meta.artifact_id) {
    chunkRows.value = []
    return
  }
  await loadChunk(chunkOffset.value)
}

async function loadChunk(offset) {
  const meta = selectedDataframeMeta.value
  if (!meta || !meta.artifact_id || !appStore.activeWorkspaceId) return
  isChunkLoading.value = true
  try {
    const payload = await apiService.getDataframeArtifactRows(
      appStore.activeWorkspaceId,
      meta.artifact_id,
      offset,
      chunkLimit,
    )
    chunkRows.value = Array.isArray(payload?.rows) ? payload.rows : []
    chunkOffset.value = Number.isFinite(payload?.offset) ? payload.offset : offset
  } catch (error) {
    console.error('Failed to load dataframe chunk:', error)
    chunkRows.value = []
  } finally {
    isChunkLoading.value = false
  }
}

async function loadPreviousChunk() {
  if (chunkOffset.value === 0 || isChunkLoading.value) return
  const nextOffset = Math.max(0, chunkOffset.value - chunkLimit)
  await loadChunk(nextOffset)
}

async function loadNextChunk() {
  if (!canLoadNextChunk.value || isChunkLoading.value) return
  await loadChunk(chunkOffset.value + chunkLimit)
}

function generateColumnDefs(data) {
  if (!data || data.length === 0) return []

  const firstRow = data[0]
  const columns = Object.keys(firstRow).map(key => {
    const sampleValue = firstRow[key]

    return {
      headerName: key,
      field: key,
      cellRenderer: getCellRenderer(sampleValue),
      tooltipField: key,
      valueGetter: params => params.data?.[key],
      cellRendererParams: {
        truncate: 120
      },
      cellStyle: { whiteSpace: 'nowrap' }
    }
  })

  return columns
}

function getCellRenderer(value) {
  const truncateLen = 120
  if (typeof value === 'number') {
    return (params) => {
      const v = params.value
      if (v == null) return '<span class="text-gray-400 italic">null</span>'
      const s = typeof v === 'number' ? v.toLocaleString() : String(v)
      const display = s.length > truncateLen ? s.slice(0, truncateLen) + '…' : s
      const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      return `<span title="${esc(s)}">${esc(display)}</span>`
    }
  }
  return (params) => {
    const v = params.value
    if (v == null) return '<span class="text-gray-400 italic">null</span>'
    const s = String(v)
    const display = s.length > truncateLen ? s.slice(0, truncateLen) + '…' : s
    const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<span title="${esc(s)}">${esc(display)}</span>`
  }
}

async function downloadCsv() {
  if (!rowData.value.length || isDownloading.value) return

  isDownloading.value = true

  try {
    const csvContent = convertToCSV(rowData.value)
    const dfName = orderedDataframes.value[selectedDataframeIndex.value]?.name || 'dataframe'

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `${dfName}_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    console.debug('CSV downloaded successfully')
  } catch (error) {
    console.error('Failed to download CSV:', error)
  } finally {
    isDownloading.value = false
  }
}

function convertToCSV(data) {
  if (!data || data.length === 0) return ''

  const headers = Object.keys(data[0])
  const csvRows = []

  csvRows.push(headers.map(header => `"${header}"`).join(','))

  for (const row of data) {
    const values = headers.map(header => {
      const value = row[header]
      if (value == null) return '""'
      return `"${String(value).replace(/"/g, '""')}"`
    })
    csvRows.push(values.join(','))
  }

  return csvRows.join('\n')
}
</script>

<style>
/* AG Grid theme customizations */
.ag-theme-alpine {
  --ag-border-color: #e5e7eb;
  --ag-header-background-color: #f9fafb;
  --ag-odd-row-background-color: #ffffff;
  --ag-even-row-background-color: #f9fafb;
  --ag-row-hover-color: #f3f4f6;
  --ag-selected-row-background-color: #dbeafe;
}

.ag-theme-alpine .ag-header-cell-label {
  font-weight: 600;
}

.ag-theme-alpine .ag-cell {
  border-right: 1px solid var(--ag-border-color);
}
</style>
