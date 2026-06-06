<template>
  <div class="flex flex-col h-full" style="background-color: var(--color-base);">
    <Teleport to="#workspace-right-pane-toolbar-center" v-if="isMounted && appStore.dataPane === 'table'">
      <div class="flex min-w-0 w-full items-center justify-center">
        <div
          v-if="displayArtifacts.length > 0"
          class="flex min-w-[11rem] w-full items-center"
          style="max-width: clamp(11rem, 34vw, 20rem);"
        >
        <HeaderDropdown
            id="dataframe-select"
            v-model="selectedArtifactId"
            :options="tableDropdownOptions"
            placeholder="Select table"
            aria-label="Select table"
            max-width-class="w-full"
          />
        </div>
      </div>
    </Teleport>

    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && appStore.dataPane === 'table'">
      <div class="flex min-w-0 items-center justify-end w-full gap-2">
        <div v-if="tableStatusMessage" class="flex items-center gap-2 text-[12px] leading-[1.3] mr-1" :class="tableStatusClass">
          <div
            v-if="isPageLoading"
            class="h-3.5 w-3.5 animate-spin rounded-full border border-[var(--color-border)] border-t-[var(--color-text-main)]"
            aria-hidden="true"
          ></div>
          <span>{{ tableStatusMessage }}</span>
        </div>

        <div
          class="relative min-w-[10rem] flex-1"
          style="max-width: clamp(9rem, 24vw, 13.5rem);"
        >
          <FunnelIcon
            class="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2"
            style="color: var(--color-text-sub);"
            title="Search rows"
            aria-hidden="true"
          />
          <input
            v-model="tableSearch"
            type="text"
            placeholder="Search rows"
            class="input-base h-8 pl-8 pr-2"
            title="Search rows in current table"
            :disabled="!selectedArtifactId"
            aria-label="Search rows"
            style="background-color: var(--color-surface); border-color: var(--color-border);"
          />
        </div>

        <!-- Delete selected table -->
        <button
          @click="openDeleteDialog"
          type="button"
          :disabled="!canDeleteSelectedArtifact || isDeletingArtifact"
          class="btn-icon h-8 w-8 shrink-0 border"
          style="border-color: var(--color-border); color: var(--color-text-muted);"
          :class="(!canDeleteSelectedArtifact || isDeletingArtifact) ? 'opacity-50 cursor-not-allowed' : ''"
          :title="isDeletingArtifact ? 'Deleting table' : 'Delete table'"
          :aria-label="isDeletingArtifact ? 'Deleting table' : 'Delete table'"
        >
          <div
            v-if="isDeletingArtifact"
            class="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-error)]"
          ></div>
          <TrashIcon v-else class="h-4 w-4" />
        </button>

        <!-- CSV download -->
        <button
          @click="downloadCsv"
          :disabled="!downloadRows.length || isDownloading"
          class="btn-icon h-8 w-8 shrink-0 border"
          style="border-color: var(--color-border); color: var(--color-text-muted);"
          :class="!downloadRows.length ? 'opacity-50 cursor-not-allowed' : ''"
          :title="isDownloading ? 'Exporting CSV' : 'Export CSV'"
          :aria-label="isDownloading ? 'Exporting CSV' : 'Export CSV'"
        >
          <ArrowDownTrayIcon v-if="!isDownloading" class="h-4 w-4" />
          <div v-else class="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-text-main)]"></div>
        </button>
      </div>
    </Teleport>

    <div class="flex-1 relative mt-1 table-pane-surface">
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
        :animateRows="false"
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
        :quickFilterText="tableSearch"
        :defaultColDef="defaultColDef"
        :enableClipboard="true"
        :pagination="true"
        :paginationPageSize="pageSize"
        :suppressMenuHide="true"
        :animateRows="false"
        @grid-pre-destroy="onGridPreDestroy"
        @grid-ready="onGridReady"
        @pagination-changed="onPaginationChanged"
      ></ag-grid-vue>

      <!-- Empty state: user hasn't selected a table yet but artifacts exist -->
      <div
        v-else-if="!selectedArtifactId && displayArtifacts.length > 0"
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <TableCellsIcon class="h-12 w-12 mx-auto mb-3" style="color: var(--color-border);" />
          <p class="text-sm font-medium" style="color: var(--color-text-muted);">
            {{ displayArtifacts.length }} table{{ displayArtifacts.length === 1 ? '' : 's' }} available
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
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-10 w-10 mx-auto mb-3 text-[var(--color-error)]">
            <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
          </svg>
          <p class="text-base font-semibold text-[var(--color-danger-text)]">Failed to load selected table</p>
          <p class="text-sm mt-2 text-[var(--color-danger-text)] break-words">{{ tableError }}</p>
          <p class="text-xs mt-3" style="color: var(--color-text-muted);">
            Table:
            <span class="font-medium">{{ selectedArtifactMeta?.display_name || selectedArtifactMeta?.logical_name || selectedArtifactId }}</span>
          </p>
          <button
            class="btn-secondary mt-4 px-3 py-1.5 text-sm leading-4"
            @click="retrySelectedArtifact"
          >
            Retry
          </button>
        </div>
      </div>

      <!-- Empty state: loading artifacts -->
      <div
        v-else-if="showArtifactListLoadingState"
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <div class="h-8 w-8 mx-auto mb-3 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-text-main)]"></div>
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
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-10 w-10 mx-auto mb-3 text-[var(--color-error)]">
            <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm font-medium text-[var(--color-danger-text)]">{{ artifactListError }}</p>
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

  <ConfirmationModal
    :is-open="isDeleteDialogOpen"
    title="Delete Table"
    :message="deleteDialogMessage"
    confirm-text="Delete"
    cancel-text="Cancel"
    @close="closeDeleteDialog"
    @confirm="deleteSelectedArtifact"
  />
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-theme-quartz.css'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import { toast } from '../../composables/useToast'
import { persistExportFile } from '../../utils/exportFile'

ModuleRegistry.registerModules([AllCommunityModule])
import {
  ArrowDownTrayIcon,
  FunnelIcon,
  TableCellsIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const pageSize = 100
const isDownloading = ref(false)
const isDeletingArtifact = ref(false)
const isDeleteDialogOpen = ref(false)
const isPageLoading = ref(false)
const isLoadingArtifacts = ref(false)

// The artifact_id the user has explicitly selected (null = nothing selected)
const selectedArtifactId = ref(null)

// Artifacts fetched from the active conversation turn.
const workspaceArtifacts = ref([])

const isMounted = ref(false)
const serverRows = ref([])
const clientRows = ref([])
const serverColumns = ref([])
const rowCountValue = ref(0)
const windowStart = ref(0)
const windowEnd = ref(0)
const useClientFallback = ref(false)
const tableSearch = ref('')
const tableError = ref('')
const artifactListError = ref('')
const pendingControllers = new Set()
let gridApi = null
let listAbortController = null
let serializedRequestQueue = Promise.resolve()
let selectedArtifactLoadToken = 0
let currentDatasourceToken = 0
let tableSearchDebounceTimer = null
const pendingRestorePageByArtifact = new Map()

onMounted(() => {
  isMounted.value = true
})

onUnmounted(() => {
  cancelPendingRequests()
  listAbortController?.abort()
  if (tableSearchDebounceTimer) {
    clearTimeout(tableSearchDebounceTimer)
    tableSearchDebounceTimer = null
  }
  gridApi = null
})

const allArtifacts = computed(() => (Array.isArray(workspaceArtifacts.value) ? workspaceArtifacts.value : []))
const displayArtifacts = computed(() => {
  return allArtifacts.value.map((artifact) => ({
    ...artifact,
    source: 'artifact',
  }))
})

const showArtifactListLoadingState = computed(() => {
  return isLoadingArtifacts.value && Boolean(String(appStore.activeTurnId || '').trim())
})

const tableDropdownOptions = computed(() => displayArtifacts.value.map((artifact) => {
  const label = artifact.display_name || artifact.logical_name || artifact.artifact_id
  return {
    value: artifact.artifact_id,
    label,
    key: artifact.artifact_id,
  }
}))

// Expose dataframe count to the store so StatusBar can read it
watch(allArtifacts, (list) => {
  if (
    selectedArtifactId.value
    && !list.some((item) => item.artifact_id === selectedArtifactId.value)
  ) {
    selectedArtifactId.value = null
  }
}, { immediate: true })

watch(displayArtifacts, (list) => {
  appStore.setDataframeCount(list.length)
  if (selectedArtifactId.value && !list.some((item) => item.artifact_id === selectedArtifactId.value)) {
    selectedArtifactId.value = null
  }
}, { immediate: true })

function resolvePreferredTableSelectionId(availableArtifactIds) {
  const currentSelection = String(selectedArtifactId.value || '').trim()
  if (currentSelection && availableArtifactIds.has(currentSelection)) return currentSelection
  return displayArtifacts.value[0]?.artifact_id || null
}

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

// ---------------------------------------------------------------------------
// Load active turn artifact list whenever the conversation turn changes
// ---------------------------------------------------------------------------
async function loadActiveTurnArtifacts() {
  const conversationId = String(appStore.activeConversationId || '').trim()
  const turnId = String(appStore.activeTurnId || '').trim()
  if (!conversationId || !turnId || !appStore.hasWorkspace) {
    workspaceArtifacts.value = []
    selectedArtifactId.value = null
    return
  }
  listAbortController?.abort()
  listAbortController = new AbortController()
  isLoadingArtifacts.value = true
  artifactListError.value = ''
  appStore.clearDataPaneError()
  try {
    const response = await enqueueSerializedRequest(() => apiService.v1ListTurnArtifacts(
      conversationId,
      turnId,
      'dataframe',
      { signal: listAbortController.signal }
    ))
    const artifacts = Array.isArray(response?.artifacts) ? response.artifacts : []
    workspaceArtifacts.value = artifacts
    const availableArtifactIds = new Set(
      displayArtifacts.value
        .map((item) => String(item?.artifact_id || '').trim())
        .filter(Boolean),
    )
    const preferredSelection = resolvePreferredTableSelectionId(availableArtifactIds)
    if (preferredSelection) {
      selectedArtifactId.value = preferredSelection
    } else {
      const currentSelection = String(selectedArtifactId.value || '').trim()
      const hasCurrentSelection = Boolean(currentSelection && availableArtifactIds.has(currentSelection))
      if (!hasCurrentSelection) {
        selectedArtifactId.value = displayArtifacts.value[0]?.artifact_id || null
      }
    }
  } catch (error) {
    if (isAbortError(error)) return
    console.warn('Failed to load active turn artifacts:', error)
    const brief = error?.response?.data?.detail || error?.message || 'Failed to load tables'
    artifactListError.value = brief
    appStore.setDataPaneError(brief)
    workspaceArtifacts.value = []
  } finally {
    isLoadingArtifacts.value = false
  }
}

watch(() => appStore.activeWorkspaceId, () => {
  tableSearch.value = ''
  pendingRestorePageByArtifact.clear()
  selectedArtifactLoadToken += 1
  selectedArtifactId.value = null
  workspaceArtifacts.value = []
  resetTableState()
}, { immediate: true })

watch(
  () => [
    String(appStore.activeConversationId || '').trim(),
    String(appStore.activeTurnId || '').trim(),
    String(appStore.activeTurnArtifactRefreshKey || 0),
  ].join('||'),
  async () => {
    if (!appStore.hasWorkspace) return

    const previousSelection = String(selectedArtifactId.value || '').trim()
    await loadActiveTurnArtifacts()

    const nextSelection = String(selectedArtifactId.value || '').trim()
    if (!nextSelection || nextSelection !== previousSelection) return

    resetTableState()

    const workspaceId = String(appStore.activeWorkspaceId || '').trim()
    const rememberedPage = appStore.getTablePageOffset(workspaceId, nextSelection)
    if (Number.isInteger(rememberedPage) && rememberedPage > 0) {
      pendingRestorePageByArtifact.set(nextSelection, rememberedPage)
    } else {
      pendingRestorePageByArtifact.delete(nextSelection)
    }

    try {
      await prepareArtifact(nextSelection)
    } catch (error) {
      if (isAbortError(error)) return
      tableError.value = error?.message || 'Failed to load selected table.'
    }
  },
)

// ---------------------------------------------------------------------------
// React to user selecting an artifact in the dropdown
// ---------------------------------------------------------------------------
watch(selectedArtifactId, async (newId) => {
  if (tableSearchDebounceTimer) {
    clearTimeout(tableSearchDebounceTimer)
    tableSearchDebounceTimer = null
  }
  const loadToken = ++selectedArtifactLoadToken
  const normalizedWorkspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (normalizedWorkspaceId) {
    appStore.setSelectedTableArtifact(normalizedWorkspaceId, String(newId || '').trim())
  }
  resetTableState()
  if (!newId) {
    appStore.clearTableViewport()
    return
  }
  const isKnownPersistedArtifact = allArtifacts.value.some(
    (entry) => String(entry?.artifact_id || '').trim() === String(newId || '').trim(),
  )
  if (!isKnownPersistedArtifact) {
    tableError.value = 'Selected table is not available for this turn.'
    return
  }
  const rememberedPage = appStore.getTablePageOffset(appStore.activeWorkspaceId, newId)
  if (Number.isInteger(rememberedPage) && rememberedPage > 0) {
    pendingRestorePageByArtifact.set(newId, rememberedPage)
  } else {
    pendingRestorePageByArtifact.delete(newId)
  }
  if (loadToken !== selectedArtifactLoadToken) return
  try {
    await prepareArtifact(newId)
  } catch (error) {
    if (isAbortError(error)) return
    tableError.value = error?.message || 'Failed to load selected table.'
  }
})

watch(tableSearch, () => {
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!artifactId) return
  if (tableSearchDebounceTimer) {
    clearTimeout(tableSearchDebounceTimer)
  }
  tableSearchDebounceTimer = setTimeout(() => {
    tableSearchDebounceTimer = null
    pendingRestorePageByArtifact.delete(artifactId)
    appStore.setTablePageOffset(appStore.activeWorkspaceId, artifactId, 0)
    if (!useInfiniteModel.value || !isGridAlive()) return
    void attachInfiniteDatasource(artifactId).then(() => {
      gridApi?.paginationGoToPage?.(0)
    })
  }, 200)
})

// ---------------------------------------------------------------------------
// Computed helpers
// ---------------------------------------------------------------------------
const selectedArtifactMeta = computed(() => {
  if (!selectedArtifactId.value) return null
  return displayArtifacts.value.find(a => a.artifact_id === selectedArtifactId.value) ?? null
})

const canDeleteSelectedArtifact = computed(() => {
  if (!selectedArtifactMeta.value) return false
  return selectedArtifactMeta.value.source === 'artifact'
})

const deleteDialogMessage = computed(() => {
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!artifactId) return 'Delete this table? This cannot be undone.'
  const artifactLabel = String(selectedArtifactMeta.value?.display_name || selectedArtifactMeta.value?.logical_name || artifactId)
  return `Delete table "${artifactLabel}"? This cannot be undone.`
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
  if (isDeletingArtifact.value) return 'Deleting table...'
  if (isPageLoading.value) return 'Loading table data...'
  if (tableError.value) return tableError.value
  return ''
})

const tableStatusClass = computed(() => {
  if (tableError.value) return 'text-[var(--color-danger-text)]'
  return 'text-[var(--color-text-main)]'
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
  appStore.clearTableViewport()
  tableError.value = ''
  useClientFallback.value = false
  if (isGridAlive()) {
    gridApi.setGridOption?.('datasource', null)
  }
}

function onGridReady(params) {
  gridApi = params.api
  if (useInfiniteModel.value) {
    void attachInfiniteDatasource().then(() => {
      restoreArtifactPage(selectedArtifactId.value)
    })
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
    appStore.clearTableViewport()
    return
  }
  const page = Math.max(0, Number(gridApi.paginationGetCurrentPage?.() || 0))
  const aid = selectedArtifactId.value
  if (aid) {
    const pendingPage = pendingRestorePageByArtifact.get(aid)
    if (Number.isInteger(pendingPage) && pendingPage > 0) {
      // Ignore the transient page-0 event fired while grid is reinitializing.
      if (page === 0) return
      if (page === pendingPage) {
        pendingRestorePageByArtifact.delete(aid)
      }
    }
    appStore.setTablePageOffset(appStore.activeWorkspaceId, aid, page)
  }
  const start = page * pageSize + 1
  const end = Math.min(total, start + pageSize - 1)
  windowStart.value = start
  windowEnd.value = end
  appStore.setTableViewport(start, end, total)
}

function restoreArtifactPage(artifactId) {
  if (!artifactId || !isGridAlive()) return
  if (String(tableSearch.value || '').trim()) return
  const rememberedPage = pendingRestorePageByArtifact.get(artifactId)
    ?? appStore.getTablePageOffset(appStore.activeWorkspaceId, artifactId)
  if (!Number.isInteger(rememberedPage) || rememberedPage <= 0) return
  const total = Number(rowCountValue.value || 0)
  if (total <= 0) return
  const maxPage = Math.max(0, Math.ceil(total / pageSize) - 1)
  const targetPage = Math.min(rememberedPage, maxPage)
  if (targetPage > 0) {
    gridApi.paginationGoToPage?.(targetPage)
  } else {
    pendingRestorePageByArtifact.delete(artifactId)
  }
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
  if (!artifactId || !appStore.activeWorkspaceId || !appStore.activeConversationId || !appStore.activeTurnId) return
  tableError.value = ''
  useClientFallback.value = false

  try {
    const workspaceId = appStore.activeWorkspaceId
    const conversationId = appStore.activeConversationId
    const turnId = appStore.activeTurnId
    await enqueueSerializedRequest(async () => {
      if (workspaceId !== appStore.activeWorkspaceId) throw createAbortError()
      if (conversationId !== appStore.activeConversationId) throw createAbortError()
      if (turnId !== appStore.activeTurnId) throw createAbortError()
      // Always use server infinite model for persisted artifacts
      clientRows.value = []
      await loadInitialServerPage(artifactId)
    })
    if (tableError.value) return
    await attachInfiniteDatasource(artifactId)
    restoreArtifactPage(artifactId)
  } catch (error) {
    if (isAbortError(error)) return
    tableError.value = error?.message || 'Failed to load selected table.'
  }
}

async function loadInitialServerPage(artifactId) {
  const conversationId = String(appStore.activeConversationId || '').trim()
  const turnId = String(appStore.activeTurnId || '').trim()
  if (!artifactId || !conversationId || !turnId) return
  isPageLoading.value = true
  const controller = new AbortController()
  pendingControllers.add(controller)
  try {
    const payload = await apiService.getTurnDataframeArtifactRows(
      conversationId,
      turnId,
      artifactId,
      0,
      pageSize,
      {
        signal: controller.signal,
        searchText: String(tableSearch.value || '').trim(),
      },
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
    appStore.setTableViewport(windowStart.value, windowEnd.value, rowCountValue.value)
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
    appStore.clearTableViewport()
  } finally {
    pendingControllers.delete(controller)
    isPageLoading.value = false
  }
}

async function attachInfiniteDatasource(artifactId) {
  const aid = artifactId || selectedArtifactId.value
  const conversationId = String(appStore.activeConversationId || '').trim()
  const turnId = String(appStore.activeTurnId || '').trim()
  if (!aid || !conversationId || !turnId) return
  cancelPendingRequests()
  currentDatasourceToken += 1
  if (!isGridAlive()) return
  const datasourceTag = currentDatasourceToken

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
          const sortModel = Array.isArray(params?.sortModel) ? params.sortModel : []
          const filterModel = (
            params?.filterModel &&
            typeof params.filterModel === 'object' &&
            !Array.isArray(params.filterModel)
          ) ? params.filterModel : {}
          return apiService.getTurnDataframeArtifactRows(
            conversationId,
            turnId,
            aid,
            startRow,
            requestLimit,
            {
              signal: controller.signal,
              sortModel,
              filterModel,
              searchText: String(tableSearch.value || '').trim(),
            },
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
        appStore.setTableViewport(windowStart.value, windowEnd.value, rowCountValue.value)
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
      if (v == null) return '<span class="text-[var(--color-text-muted)] italic">null</span>'
      const s = typeof v === 'number' ? v.toLocaleString() : String(v)
      const display = s.length > truncateLen ? s.slice(0, truncateLen) + '…' : s
      const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      return `<span title="${esc(s)}">${esc(display)}</span>`
    }
  }
  return (params) => {
    const v = params.value
    if (v == null) return '<span class="text-[var(--color-text-muted)] italic">null</span>'
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
    const dfName = selectedArtifactMeta.value?.logical_name || selectedArtifactMeta.value?.display_name || 'dataframe'
    const filename = `${dfName}_${new Date().toISOString().split('T')[0]}.csv`
    const bytes = new TextEncoder().encode(csvContent)
    const exported = await persistExportFile({
      defaultFileName: filename,
      mimeType: 'text/csv;charset=utf-8;',
      payload: bytes,
      tauriFilters: [{ name: 'CSV File', extensions: ['csv'] }],
      browserFileTypes: [{ description: 'CSV File', accept: { 'text/csv': ['.csv'] } }]
    })
    if (!exported) {
      toast.info('Export canceled')
      return
    }
    toast.success('Export complete', `${filename} saved.`)
  } catch (error) {
    console.error('Failed to download CSV:', error)
    toast.error('Export failed', 'Unable to save CSV file.')
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

function openDeleteDialog() {
  if (!canDeleteSelectedArtifact.value || isDeletingArtifact.value) return
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  if (isDeletingArtifact.value) return
  isDeleteDialogOpen.value = false
}

async function deleteSelectedArtifact() {
  const conversationId = String(appStore.activeConversationId || '').trim()
  const turnId = String(appStore.activeTurnId || '').trim()
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!conversationId || !turnId || !artifactId || isDeletingArtifact.value) return

  isDeleteDialogOpen.value = false
  isDeletingArtifact.value = true
  tableError.value = ''
  try {
    await apiService.v1DeleteTurnArtifact(conversationId, turnId, artifactId)
    await loadActiveTurnArtifacts()
    const remainingArtifactId = allArtifacts.value[0]?.artifact_id || null
    selectedArtifactId.value = remainingArtifactId
    if (!remainingArtifactId) {
      resetTableState()
      appStore.clearTableViewport()
    }
  } catch (error) {
    if (isAbortError(error)) return
    tableError.value = error?.message || 'Failed to delete table artifact.'
  } finally {
    isDeletingArtifact.value = false
  }
}
</script>

<style>
.ag-theme-quartz {
  --ag-background-color: var(--color-base);
  --ag-header-background-color: var(--color-surface);
  --ag-header-height: 34px;
  --ag-row-height: 30px;
  --ag-grid-size: 4px;
  --ag-cell-horizontal-padding: 8px;
  --ag-header-cell-horizontal-padding: 8px;
  --ag-odd-row-background-color: var(--color-base);
  --ag-even-row-background-color: var(--color-surface);
  --ag-row-hover-color: var(--color-base-muted);
  --ag-selected-row-background-color: var(--color-accent-soft);
  --ag-border-color: var(--color-border);
  --ag-header-foreground-color: var(--color-text-main);
  --ag-foreground-color: var(--color-text-main);
  --ag-secondary-foreground-color: var(--color-text-muted);
  --ag-input-focus-border-color: var(--color-accent);
  --ag-range-selection-border-color: var(--color-border-hover);
  --ag-cell-horizontal-border: solid var(--color-border);
  --ag-header-column-separator-color: var(--color-border);
  --ag-header-column-separator-display: block;
  --ag-icon-color: var(--color-text-sub);
  --ag-active-color: var(--color-accent);
}

.ag-theme-quartz .ag-header {
  border-bottom: 1px solid var(--color-border);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--color-text-main);
}

.ag-theme-quartz .ag-cell,
.ag-theme-quartz .ag-header-cell {
  border-right: 1px solid var(--color-border);
}

.ag-theme-quartz .ag-cell {
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  color: var(--color-text-main);
}

.ag-theme-quartz .ag-row .ag-cell:last-child,
.ag-theme-quartz .ag-header-row .ag-header-cell:last-child {
  border-right: none;
}

.ag-theme-quartz .ag-icon {
  color: var(--color-text-sub);
}

.ag-theme-quartz .ag-header-cell-sorted-asc .ag-icon,
.ag-theme-quartz .ag-header-cell-sorted-desc .ag-icon,
.ag-theme-quartz .ag-header-cell-filtered .ag-icon {
  color: var(--color-accent);
}

.ag-theme-quartz .ag-root-wrapper,
.ag-theme-quartz .ag-root,
.ag-theme-quartz .ag-center-cols-viewport,
.ag-theme-quartz .ag-center-cols-container,
.ag-theme-quartz .ag-body-viewport,
.ag-theme-quartz .ag-body {
  background-color: var(--color-base);
}

.ag-theme-quartz .ag-paging-panel {
  background-color: var(--color-surface);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-main);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 400;
  line-height: 1.3;
}

.ag-theme-quartz .ag-paging-button[aria-current='page'] {
  color: var(--color-accent);
  font-weight: 500;
}

.table-pane-surface {
  background-color: var(--color-base);
}
</style>
