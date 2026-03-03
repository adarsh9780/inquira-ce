<template>
  <div class="flex flex-col h-full">
    <Teleport to="#workspace-right-pane-toolbar" v-if="isMounted && appStore.dataPane === 'table'">
      <div class="flex items-center justify-end w-full gap-4">
        <!-- Loading / error status (left) -->
        <div class="flex items-center space-x-3 text-sm mr-auto">
          <div v-if="tableStatusMessage" class="flex items-center gap-2 text-xs" :class="tableStatusClass">
            <div
              v-if="isPageLoading"
              class="h-3.5 w-3.5 animate-spin rounded-full border border-gray-300 border-t-gray-800"
              aria-hidden="true"
            ></div>
            <span>{{ tableStatusMessage }}</span>
          </div>
          <span v-else-if="selectedArtifactId && rowCount > 0" class="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
            {{ rowCount.toLocaleString() }} rows
          </span>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Pagination info -->
          <div v-if="selectedArtifactId && rowCount > 0" class="flex items-center space-x-2 text-xs text-gray-600">
            <span>
              Showing {{ windowStart.toLocaleString() }}-{{ windowEnd.toLocaleString() }}
              of {{ rowCount.toLocaleString() }}
            </span>
          </div>

          <!-- Table selector dropdown — always shown when artifacts are available -->
          <div v-if="allArtifacts.length > 0" class="flex items-center space-x-2">
            <select
              id="dataframe-select"
              v-model="selectedArtifactId"
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-w-[200px]"
            >
              <option :value="null" disabled>— select a table —</option>
              <option
                v-for="artifact in allArtifacts"
                :key="artifact.artifact_id"
                :value="artifact.artifact_id"
              >
                {{ artifact.logical_name }}
              </option>
            </select>
          </div>

          <!-- CSV download -->
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
      <!-- Grid: infinite model -->
      <ag-grid-vue
        v-if="selectedArtifactId && hasRenderableRows && useInfiniteModel"
        :key="`infinite-${selectedArtifactId}`"
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
        @grid-pre-destroy="onGridPreDestroy"
        @grid-ready="onGridReady"
        @pagination-changed="onPaginationChanged"
      ></ag-grid-vue>

      <!-- Grid: client-side fallback -->
      <ag-grid-vue
        v-else-if="selectedArtifactId && hasRenderableRows"
        :key="`client-${selectedArtifactId}`"
        class="ag-theme-quartz absolute inset-0"
        :columnDefs="columnDefs"
        :rowData="clientRows"
        :defaultColDef="defaultColDef"
        :enableClipboard="true"
        :pagination="true"
        :paginationPageSize="pageSize"
        :suppressMenuHide="true"
        :animateRows="true"
        @grid-pre-destroy="onGridPreDestroy"
        @grid-ready="onGridReady"
        @pagination-changed="onPaginationChanged"
      ></ag-grid-vue>

      <!-- Empty state: user hasn't selected a table yet but artifacts exist -->
      <div
        v-else-if="!selectedArtifactId && allArtifacts.length > 0"
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <TableCellsIcon class="h-12 w-12 mx-auto mb-3" style="color: var(--color-border);" />
          <p class="text-sm font-medium" style="color: var(--color-text-muted);">
            {{ allArtifacts.length }} table{{ allArtifacts.length === 1 ? '' : 's' }} available
          </p>
          <p class="text-xs mt-1" style="color: var(--color-text-muted);">Select a table from the dropdown above</p>
        </div>
      </div>

      <!-- Selected artifact failed to load -->
      <div
        v-else-if="selectedArtifactId && tableError"
        class="absolute inset-0 flex items-center justify-center px-8"
        style="background-color: var(--color-base);"
      >
        <div class="max-w-3xl w-full text-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-10 w-10 mx-auto mb-3 text-red-500">
            <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
          </svg>
          <p class="text-base font-semibold text-red-700">Failed to load selected table</p>
          <p class="text-sm mt-2 text-red-700 break-words">{{ tableError }}</p>
          <p class="text-xs mt-3" style="color: var(--color-text-muted);">
            Table:
            <span class="font-medium">{{ selectedArtifactMeta?.logical_name || selectedArtifactId }}</span>
          </p>
          <button
            class="mt-4 inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            @click="retrySelectedArtifact"
          >
            Retry
          </button>
        </div>
      </div>

      <!-- Empty state: loading artifacts -->
      <div
        v-else-if="isLoadingArtifacts"
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <div class="h-8 w-8 mx-auto mb-3 animate-spin rounded-full border-2 border-gray-300 border-t-gray-700"></div>
          <p class="text-xs" style="color: var(--color-text-muted);">Loading saved tables…</p>
        </div>
      </div>

      <!-- Empty state: error loading artifacts -->
      <div
        v-else-if="artifactListError"
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-10 w-10 mx-auto mb-3 text-red-400">
            <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm font-medium text-red-600">{{ artifactListError }}</p>
          <p class="text-xs mt-1" style="color: var(--color-text-muted);">Try restarting the kernel</p>
        </div>
      </div>

      <!-- Empty state: no artifacts at all -->
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
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
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
const isLoadingArtifacts = ref(false)

// The artifact_id the user has explicitly selected (null = nothing selected)
const selectedArtifactId = ref(null)

// Artifacts fetched from the workspace scratchpad (persisted from previous runs)
const workspaceArtifacts = ref([])

const isMounted = ref(false)
const serverRows = ref([])
const clientRows = ref([])
const serverColumns = ref([])
const rowCountValue = ref(0)
const windowStart = ref(0)
const windowEnd = ref(0)
const useClientFallback = ref(false)
const tableError = ref('')
const artifactListError = ref('')
const pendingControllers = new Set()
let gridApi = null
let listAbortController = null
let kernelReadyWorkspaceId = ''
let serializedRequestQueue = Promise.resolve()
let selectedArtifactLoadToken = 0
let currentDatasourceToken = 0

onMounted(() => {
  isMounted.value = true
})

onUnmounted(() => {
  cancelPendingRequests()
  listAbortController?.abort()
  gridApi = null
})

// ---------------------------------------------------------------------------
// Merge workspace-persisted artifacts with any live-run dataframes from the
// chat history (appStore.dataframes).  Live entries take precedence if they
// share the same artifact_id.
// ---------------------------------------------------------------------------
const allArtifacts = computed(() => {
  const map = new Map()

  // 1. Workspace-persisted (from scratchpad)
  for (const a of workspaceArtifacts.value) {
    map.set(a.artifact_id, {
      artifact_id: a.artifact_id,
      logical_name: a.logical_name,
      row_count: a.row_count,
    })
  }

  // 2. Live dataframes produced in the current session
  for (const df of appStore.dataframes) {
    const id = df?.data?.artifact_id
    if (!id) continue
    map.set(id, {
      artifact_id: id,
      logical_name: df.name || 'dataframe',
      row_count: df?.data?.row_count ?? null,
    })
  }

  return [...map.values()]
})

// Expose dataframe count to the store so StatusBar can read it
watch(allArtifacts, (list) => {
  appStore.setDataframeCount(list.length)
}, { immediate: true })

function createAbortError(message = 'Request aborted') {
  const error = new Error(message)
  error.name = 'AbortError'
  return error
}

function isAbortError(error) {
  return error?.name === 'AbortError'
}

function enqueueSerializedRequest(task) {
  const next = serializedRequestQueue.catch(() => {}).then(task)
  serializedRequestQueue = next.catch(() => {})
  return next
}

function waitMs(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup()
      resolve()
    }, ms)
    const onAbort = () => {
      cleanup()
      reject(createAbortError())
    }
    const cleanup = () => {
      clearTimeout(timer)
      signal?.removeEventListener?.('abort', onAbort)
    }
    if (signal?.aborted) {
      cleanup()
      reject(createAbortError())
      return
    }
    signal?.addEventListener?.('abort', onAbort, { once: true })
  })
}

async function waitForKernelReady(workspaceId, signal) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) {
    throw new Error('No active workspace selected.')
  }
  if (kernelReadyWorkspaceId === normalizedWorkspaceId) {
    return
  }

  const timeoutMs = 120000
  const pollIntervalMs = 700
  const start = Date.now()
  let lastStatus = 'unknown'

  while (Date.now() - start < timeoutMs) {
    if (signal?.aborted) throw createAbortError()

    const statusPayload = await apiService.v1GetWorkspaceKernelStatus(normalizedWorkspaceId)
    const status = String(statusPayload?.status || '').trim().toLowerCase()
    lastStatus = status || lastStatus

    if (status === 'ready') {
      kernelReadyWorkspaceId = normalizedWorkspaceId
      return
    }

    await waitMs(pollIntervalMs, signal)
  }

  throw new Error(`Kernel did not become ready in 120 seconds (last status: ${lastStatus}).`)
}

// ---------------------------------------------------------------------------
// Load workspace artifact list whenever the workspace changes
// ---------------------------------------------------------------------------
async function loadWorkspaceArtifacts(workspaceId) {
  if (!workspaceId) {
    workspaceArtifacts.value = []
    return
  }
  listAbortController?.abort()
  listAbortController = new AbortController()
  isLoadingArtifacts.value = true
  artifactListError.value = ''
  appStore.clearDataPaneError()
  try {
    const response = await enqueueSerializedRequest(async () => {
      await waitForKernelReady(workspaceId, listAbortController.signal)
      return apiService.v1ListWorkspaceArtifacts(
        workspaceId,
        'dataframe',
        { signal: listAbortController.signal }
      )
    })
    workspaceArtifacts.value = Array.isArray(response?.artifacts) ? response.artifacts : []
  } catch (error) {
    if (isAbortError(error)) return
    console.warn('Failed to load workspace artifacts:', error)
    const brief = error?.response?.data?.detail || error?.message || 'Failed to load tables'
    artifactListError.value = brief
    appStore.setDataPaneError(brief)
    workspaceArtifacts.value = []
  } finally {
    isLoadingArtifacts.value = false
  }
}

watch(() => appStore.activeWorkspaceId, (id) => {
  kernelReadyWorkspaceId = ''
  selectedArtifactLoadToken += 1
  selectedArtifactId.value = null
  resetTableState()
  loadWorkspaceArtifacts(id)
}, { immediate: true })

// ---------------------------------------------------------------------------
// React to user selecting an artifact in the dropdown
// ---------------------------------------------------------------------------
watch(selectedArtifactId, async (newId) => {
  const loadToken = ++selectedArtifactLoadToken
  resetTableState()
  if (!newId) return
  if (loadToken !== selectedArtifactLoadToken) return
  try {
    await prepareArtifact(newId)
  } catch (error) {
    if (isAbortError(error)) return
    tableError.value = error?.message || 'Failed to load selected table.'
  }
})

// ---------------------------------------------------------------------------
// Computed helpers
// ---------------------------------------------------------------------------
const selectedArtifactMeta = computed(() => {
  if (!selectedArtifactId.value) return null
  return allArtifacts.value.find(a => a.artifact_id === selectedArtifactId.value) ?? null
})

const useInfiniteModel = computed(() => {
  return !!selectedArtifactId.value && !useClientFallback.value
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

const tableStatusMessage = computed(() => {
  if (isPageLoading.value) return 'Loading table data...'
  if (tableError.value) return tableError.value
  return ''
})

const tableStatusClass = computed(() => {
  if (tableError.value) return 'text-red-700'
  return 'text-gray-800'
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

// ---------------------------------------------------------------------------
// Grid lifecycle
// ---------------------------------------------------------------------------
function isGridAlive() {
  if (!gridApi) return false
  if (typeof gridApi.isDestroyed === 'function') {
    return !gridApi.isDestroyed()
  }
  return true
}

function cancelPendingRequests() {
  for (const controller of pendingControllers) {
    try { controller.abort() } catch (_) { /* no-op */ }
  }
  pendingControllers.clear()
}

function resetTableState() {
  currentDatasourceToken += 1
  cancelPendingRequests()
  clientRows.value = []
  serverRows.value = []
  serverColumns.value = []
  rowCountValue.value = 0
  windowStart.value = 0
  windowEnd.value = 0
  tableError.value = ''
  useClientFallback.value = false
  if (isGridAlive()) {
    gridApi.setGridOption?.('datasource', null)
  }
}

function onGridReady(params) {
  gridApi = params.api
  if (useInfiniteModel.value) {
    void attachInfiniteDatasource()
  }
}

function onGridPreDestroy() {
  currentDatasourceToken += 1
  cancelPendingRequests()
  gridApi = null
}

function onPaginationChanged() {
  if (!isGridAlive()) return
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

function columnsChanged(nextColumns) {
  if (!Array.isArray(nextColumns)) return false
  if (nextColumns.length !== serverColumns.value.length) return true
  for (let i = 0; i < nextColumns.length; i += 1) {
    if (String(nextColumns[i]) !== String(serverColumns.value[i])) return true
  }
  return false
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
async function prepareArtifact(artifactId) {
  if (!artifactId || !appStore.activeWorkspaceId) return
  tableError.value = ''
  useClientFallback.value = false

  try {
    const workspaceId = appStore.activeWorkspaceId
    await enqueueSerializedRequest(async () => {
      await waitForKernelReady(workspaceId, listAbortController?.signal || null)
      if (workspaceId !== appStore.activeWorkspaceId) throw createAbortError()
      // Always use server infinite model for persisted artifacts
      clientRows.value = []
      await loadInitialServerPage(artifactId)
    })
    if (tableError.value) return
    await attachInfiniteDatasource(artifactId)
  } catch (error) {
    if (isAbortError(error)) return
    tableError.value = error?.message || 'Failed to load selected table.'
  }
}

async function loadInitialServerPage(artifactId) {
  if (!artifactId || !appStore.activeWorkspaceId) return
  isPageLoading.value = true
  const controller = new AbortController()
  pendingControllers.add(controller)
  try {
    const payload = await apiService.getDataframeArtifactRows(
      appStore.activeWorkspaceId,
      artifactId,
      0,
      pageSize,
      { signal: controller.signal },
    )
    const rows = Array.isArray(payload?.rows) ? payload.rows : []
    serverRows.value = rows
    const nextColumns = Array.isArray(payload?.columns)
      ? payload.columns.map((c) => String(c))
      : (rows[0] ? Object.keys(rows[0]) : [])
    if (columnsChanged(nextColumns)) {
      serverColumns.value = nextColumns
    }
    rowCountValue.value = Number(payload?.row_count || rows.length || 0)
    clientRows.value = rows
    windowStart.value = rows.length > 0 ? 1 : 0
    windowEnd.value = rows.length > 0 ? Math.min(pageSize, rowCountValue.value || rows.length) : 0
  } catch (error) {
    if (isAbortError(error)) return
    console.error('Failed to load initial dataframe page:', error)
    tableError.value = error?.message || 'Failed to load table data.'
    serverRows.value = []
    serverColumns.value = []
    clientRows.value = []
    rowCountValue.value = 0
    windowStart.value = 0
    windowEnd.value = 0
  } finally {
    pendingControllers.delete(controller)
    isPageLoading.value = false
  }
}

async function attachInfiniteDatasource(artifactId) {
  const aid = artifactId || selectedArtifactId.value
  if (!aid || !appStore.activeWorkspaceId) return
  cancelPendingRequests()
  currentDatasourceToken += 1
  if (!isGridAlive()) return
  const datasourceTag = currentDatasourceToken

  const workspaceId = appStore.activeWorkspaceId
  const datasource = {
    rowCount: null,
    getRows: async (params) => {
      isPageLoading.value = true
      const controller = new AbortController()
      pendingControllers.add(controller)
      try {
        const payload = await enqueueSerializedRequest(async () => {
          const startRow = Number(params.startRow || 0)
          const endRow = Number(params.endRow || (startRow + pageSize))
          const requestLimit = Math.max(1, Math.min(pageSize, endRow - startRow))
          return apiService.getDataframeArtifactRows(
            workspaceId,
            aid,
            startRow,
            requestLimit,
            { signal: controller.signal },
          )
        })
        if (!isGridAlive() || datasourceTag !== currentDatasourceToken) return
        const startRow = Number(params.startRow || 0)
        const rows = Array.isArray(payload?.rows) ? payload.rows : []
        serverRows.value = rows
        if (Array.isArray(payload?.columns) && payload.columns.length > 0) {
          const nextColumns = payload.columns.map((c) => String(c))
          if (columnsChanged(nextColumns)) {
            serverColumns.value = nextColumns
          }
        } else if (rows[0]) {
          const nextColumns = Object.keys(rows[0])
          if (columnsChanged(nextColumns)) {
            serverColumns.value = nextColumns
          }
        }
        rowCountValue.value = Number(payload?.row_count || rowCountValue.value || 0)
        const knownLastRow = Number.isFinite(rowCountValue.value) ? rowCountValue.value : undefined
        params.successCallback(rows, knownLastRow)
        windowStart.value = rows.length > 0 ? startRow + 1 : 0
        windowEnd.value = rows.length > 0 ? startRow + rows.length : 0
      } catch (error) {
        if (isAbortError(error)) return
        console.error('Failed to load dataframe page:', error)
        if (!isGridAlive() || datasourceTag !== currentDatasourceToken) return
        tableError.value = error?.message || 'Failed to load paginated table data.'
        // Fail once and stop AG Grid retries that can flood the backend.
        if (typeof gridApi?.setGridOption === 'function') {
          gridApi.setGridOption('datasource', null)
        } else if (typeof gridApi?.setDatasource === 'function') {
          gridApi.setDatasource(null)
        }
        params.successCallback([], Number(rowCountValue.value || 0))
      } finally {
        pendingControllers.delete(controller)
        if (datasourceTag === currentDatasourceToken) {
          isPageLoading.value = false
        }
      }
    }
  }

  if (!isGridAlive()) return
  if (typeof gridApi.setGridOption === 'function') {
    gridApi.setGridOption('datasource', datasource)
  } else if (typeof gridApi.setDatasource === 'function') {
    gridApi.setDatasource(datasource)
  }
}

// ---------------------------------------------------------------------------
// Column / cell helpers
// ---------------------------------------------------------------------------
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
      cellRendererParams: { truncate: 120 },
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

// ---------------------------------------------------------------------------
// CSV download
// ---------------------------------------------------------------------------
async function downloadCsv() {
  if (!downloadRows.value.length || isDownloading.value) return
  isDownloading.value = true
  try {
    const csvContent = convertToCSV(downloadRows.value)
    const dfName = selectedArtifactMeta.value?.logical_name || 'dataframe'
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `${dfName}_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Failed to download CSV:', error)
  } finally {
    isDownloading.value = false
  }
}

function convertToCSV(data) {
  if (!data || data.length === 0) return ''
  const headers = Object.keys(data[0])
  const csvRows = [headers.map(header => `"${header}"`).join(',')]
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

async function retrySelectedArtifact() {
  if (!selectedArtifactId.value) return
  resetTableState()
  try {
    await prepareArtifact(selectedArtifactId.value)
  } catch (error) {
    if (isAbortError(error)) return
    tableError.value = error?.message || 'Failed to load selected table.'
  }
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
