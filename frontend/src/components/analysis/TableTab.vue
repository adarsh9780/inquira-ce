<template>
  <div class="flex flex-col h-full">
    <Teleport to="#workspace-right-pane-toolbar" v-if="isMounted && appStore.dataPane === 'table'">
      <div class="flex items-center justify-end w-full gap-4">
        <div class="flex items-center space-x-3 text-sm mr-auto">
          <span v-if="appStore.isCodeRunning || isPageLoading" class="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
            Processing
          </span>
          <span v-else-if="rowCount > 0" class="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
            {{ rowCount.toLocaleString() }} rows
          </span>
        </div>

        <div class="flex items-center space-x-2">
          <div v-if="rowCount > 0" class="flex items-center space-x-2 text-xs text-gray-600">
            <span>
              Showing {{ windowStart.toLocaleString() }}-{{ windowEnd.toLocaleString() }}
              of {{ rowCount.toLocaleString() }}
            </span>
          </div>

          <div v-if="orderedDataframes && orderedDataframes.length > 1" class="flex items-center space-x-2">
            <select
              id="dataframe-select"
              v-model="selectedDataframeIndex"
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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

          <button
            @click="downloadCsv"
            :disabled="!downloadRows.length || isDownloading"
            class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!downloadRows.length ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <ArrowDownTrayIcon v-if="!isDownloading" class="h-4 w-4 mr-1" />
            <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1"></div>
            {{ isDownloading ? 'Downloading...' : 'CSV' }}
          </button>
        </div>
      </div>
    </Teleport>

    <div class="flex-1 relative mt-1">
      <ag-grid-vue
        v-if="hasRenderableRows && useInfiniteModel"
        :key="`infinite-${selectedDataframeIndex}-${datasourceVersion}`"
        class="ag-theme-quartz absolute inset-0"
        :columnDefs="columnDefs"
        :defaultColDef="defaultColDef"
        :enableClipboard="true"
        :pagination="true"
        :paginationPageSize="pageSize"
        :cacheBlockSize="pageSize"
        rowModelType="infinite"
        :suppressMenuHide="true"
        :animateRows="true"
        :rowSelection="rowSelection"
        @grid-ready="onGridReady"
        @pagination-changed="onPaginationChanged"
      ></ag-grid-vue>

      <ag-grid-vue
        v-else-if="hasRenderableRows"
        :key="`client-${selectedDataframeIndex}`"
        class="ag-theme-quartz absolute inset-0"
        :columnDefs="columnDefs"
        :rowData="clientRows"
        :defaultColDef="defaultColDef"
        :enableClipboard="true"
        :pagination="true"
        :paginationPageSize="pageSize"
        :suppressMenuHide="true"
        :animateRows="true"
        :rowSelection="rowSelection"
        @grid-ready="onGridReady"
        @pagination-changed="onPaginationChanged"
      ></ag-grid-vue>

      <div
        v-else
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <TableCellsIcon class="h-12 w-12 mx-auto mb-3" style="color: var(--color-border);" />
          <p class="text-sm" style="color: var(--color-text-muted);">No data to display</p>
          <p class="text-xs mt-1" style="color: var(--color-text-muted);">Run code to generate table data</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-theme-quartz.css'

ModuleRegistry.registerModules([AllCommunityModule])
import {
  ArrowDownTrayIcon,
  TableCellsIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const pageSize = 100
const isDownloading = ref(false)
const isPageLoading = ref(false)
const selectedDataframeIndex = ref(0)
const isMounted = ref(false)
const serverRows = ref([])
const clientRows = ref([])
const serverColumns = ref([])
const rowCountValue = ref(0)
const windowStart = ref(0)
const windowEnd = ref(0)
const datasourceVersion = ref(0)
let gridApi = null

onMounted(() => {
  isMounted.value = true
})

const orderedDataframes = computed(() => {
  if (!appStore.dataframes) return []
  return [...appStore.dataframes].slice().reverse()
})

const selectedDataframeMeta = computed(() => {
  if (!orderedDataframes.value || orderedDataframes.value.length === 0) return null
  const df = orderedDataframes.value[selectedDataframeIndex.value]
  if (!df || !df.data) return null
  return df.data
})

const useInfiniteModel = computed(() => {
  const meta = selectedDataframeMeta.value
  return !!meta?.artifact_id
})

const rowCount = computed(() => {
  if (useInfiniteModel.value) return Number(rowCountValue.value || 0)
  return Number(clientRows.value.length || 0)
})

const downloadRows = computed(() => {
  if (useInfiniteModel.value) return Array.isArray(serverRows.value) ? serverRows.value : []
  return Array.isArray(clientRows.value) ? clientRows.value : []
})

const hasRenderableRows = computed(() => {
  if (useInfiniteModel.value) return rowCount.value > 0
  return clientRows.value.length > 0
})

const columnDefs = computed(() => {
  if (serverColumns.value.length > 0) {
    return serverColumns.value.map((name) => ({
      headerName: String(name),
      field: String(name),
      cellRenderer: getCellRenderer(null),
      tooltipField: String(name),
      valueGetter: (params) => params.data?.[String(name)],
      cellRendererParams: { truncate: 120 },
      cellStyle: { whiteSpace: 'nowrap' }
    }))
  }
  const sourceRows = downloadRows.value
  if (!sourceRows || sourceRows.length === 0) return []
  return generateColumnDefs(sourceRows)
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
      await prepareSelectedDataframe()
    } else {
      clientRows.value = []
      serverRows.value = []
      serverColumns.value = []
      rowCountValue.value = 0
      windowStart.value = 0
      windowEnd.value = 0
      if (gridApi) {
        gridApi.setGridOption?.('datasource', null)
      }
    }
  },
  { immediate: true },
)

watch(selectedDataframeIndex, async () => {
  await prepareSelectedDataframe()
})

function onGridReady(params) {
  gridApi = params.api
  if (useInfiniteModel.value) {
    void attachInfiniteDatasource()
  }
}

function onPaginationChanged() {
  if (!gridApi) return
  const total = rowCount.value
  if (total <= 0) {
    windowStart.value = 0
    windowEnd.value = 0
    return
  }
  const page = Math.max(0, Number(gridApi.paginationGetCurrentPage?.() || 0))
  const start = page * pageSize + 1
  const end = Math.min(total, start + pageSize - 1)
  windowStart.value = start
  windowEnd.value = end
}

async function prepareSelectedDataframe() {
  const meta = selectedDataframeMeta.value
  if (!meta) {
    clientRows.value = []
    serverRows.value = []
    serverColumns.value = []
    rowCountValue.value = 0
    windowStart.value = 0
    windowEnd.value = 0
    return
  }

  if (useInfiniteModel.value) {
    clientRows.value = []
    await loadInitialServerPage()
    await attachInfiniteDatasource()
    return
  }

  serverRows.value = []
  serverColumns.value = []
  if (Array.isArray(meta)) {
    clientRows.value = meta
  } else if (Array.isArray(meta.data)) {
    clientRows.value = meta.data
  } else {
    clientRows.value = []
  }
  rowCountValue.value = clientRows.value.length
  windowStart.value = clientRows.value.length > 0 ? 1 : 0
  windowEnd.value = clientRows.value.length > 0 ? Math.min(pageSize, clientRows.value.length) : 0
}

async function loadInitialServerPage() {
  const meta = selectedDataframeMeta.value
  if (!meta?.artifact_id || !appStore.activeWorkspaceId) {
    serverRows.value = []
    serverColumns.value = []
    rowCountValue.value = 0
    return
  }
  isPageLoading.value = true
  try {
    const payload = await apiService.getDataframeArtifactRows(
      appStore.activeWorkspaceId,
      meta.artifact_id,
      0,
      pageSize,
    )
    const rows = Array.isArray(payload?.rows) ? payload.rows : []
    serverRows.value = rows
    serverColumns.value = Array.isArray(payload?.columns) ? payload.columns.map((c) => String(c)) : (rows[0] ? Object.keys(rows[0]) : [])
    rowCountValue.value = Number(payload?.row_count || rows.length || 0)
    windowStart.value = rows.length > 0 ? 1 : 0
    windowEnd.value = rows.length > 0 ? Math.min(pageSize, rowCountValue.value || rows.length) : 0
  } catch (error) {
    console.error('Failed to load initial dataframe page:', error)
    serverRows.value = []
    serverColumns.value = []
    rowCountValue.value = 0
    windowStart.value = 0
    windowEnd.value = 0
  } finally {
    isPageLoading.value = false
  }
}

async function attachInfiniteDatasource() {
  const meta = selectedDataframeMeta.value
  if (!meta?.artifact_id || !appStore.activeWorkspaceId) return
  datasourceVersion.value += 1
  if (!gridApi) return

  const artifactId = meta.artifact_id
  const workspaceId = appStore.activeWorkspaceId
  const datasource = {
    rowCount: null,
    getRows: async (params) => {
      isPageLoading.value = true
      try {
        const startRow = Number(params.startRow || 0)
        const endRow = Number(params.endRow || (startRow + pageSize))
        const requestLimit = Math.max(1, Math.min(pageSize, endRow - startRow))
        const payload = await apiService.getDataframeArtifactRows(
          workspaceId,
          artifactId,
          startRow,
          requestLimit,
        )
        const rows = Array.isArray(payload?.rows) ? payload.rows : []
        serverRows.value = rows
        if (Array.isArray(payload?.columns) && payload.columns.length > 0) {
          serverColumns.value = payload.columns.map((c) => String(c))
        } else if (rows[0]) {
          serverColumns.value = Object.keys(rows[0])
        }
        rowCountValue.value = Number(payload?.row_count || rowCountValue.value || 0)
        const knownLastRow = Number.isFinite(rowCountValue.value) ? rowCountValue.value : undefined
        params.successCallback(rows, knownLastRow)
        windowStart.value = rows.length > 0 ? startRow + 1 : 0
        windowEnd.value = rows.length > 0 ? startRow + rows.length : 0
      } catch (error) {
        console.error('Failed to load dataframe page:', error)
        params.failCallback()
      } finally {
        isPageLoading.value = false
      }
    }
  }

  if (typeof gridApi.setGridOption === 'function') {
    gridApi.setGridOption('datasource', datasource)
  } else if (typeof gridApi.setDatasource === 'function') {
    gridApi.setDatasource(datasource)
  }
}

function generateColumnDefs(data) {
  if (!data || data.length === 0) return []

  const firstRow = data[0]
  return Object.keys(firstRow).map((key) => {
    const sampleValue = firstRow[key]
    return {
      headerName: key,
      field: key,
      cellRenderer: getCellRenderer(sampleValue),
      tooltipField: key,
      valueGetter: (params) => params.data?.[key],
      cellRendererParams: {
        truncate: 120
      },
      cellStyle: { whiteSpace: 'nowrap' }
    }
  })
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
  if (!downloadRows.value.length || isDownloading.value) return

  isDownloading.value = true

  try {
    const csvContent = convertToCSV(downloadRows.value)
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
.ag-theme-quartz {
  --ag-background-color: #FDFCF8;
  --ag-header-background-color: #F5F3ED;
  --ag-odd-row-background-color: #FDFCF8;
  --ag-even-row-background-color: #FAF8F3;
  --ag-row-hover-color: #F0EDE5;
  --ag-selected-row-background-color: #EDE9DE;
  --ag-border-color: #E8E4DC;
  --ag-header-foreground-color: #3d3830;
  --ag-foreground-color: #1a1612;
  --ag-secondary-foreground-color: #6b6358;
  --ag-input-focus-border-color: #d4b896;
  --ag-range-selection-border-color: #c8a87c;
  --ag-cell-horizontal-border: solid #E8E4DC;
}
</style>
