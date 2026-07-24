<template>
  <div class="flex flex-col h-full" style="background-color: var(--color-base);">
    <Teleport to="#workspace-right-pane-toolbar-center" v-if="isMounted && appStore.dataPane === 'table'">
      <div v-if="tableDropdownOptions.length > 0" class="flex min-w-[11rem] max-w-full items-center" style="width: clamp(11rem, 28vw, 19rem);">
        <HeaderDropdown
          id="dataframe-select"
          v-model="selectedArtifactId"
          :options="tableDropdownOptions"
          placeholder="Select table"
          aria-label="Select table"
          max-width-class="w-full"
        />
      </div>
    </Teleport>

    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && appStore.dataPane === 'table'">
      <TableToolbar>
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
        <button
          ref="tableActionsButtonRef"
          type="button"
          class="btn-icon h-8 w-8 shrink-0 border"
          style="border-color: var(--color-border); color: var(--color-text-muted);"
          title="Table actions"
          aria-label="Table actions"
          @click="toggleTableActions"
        >
          <EllipsisHorizontalIcon class="h-4 w-4" />
        </button>
      </TableToolbar>
    </Teleport>

    <TableGridShell>
      <DataTable
        v-if="selectedArtifactId && hasRenderableRows"
        :key="`${useServerModel ? 'server' : 'client'}-${selectedArtifactId}`"
        :rows="visibleTableRows"
        :columns="tableColumns"
        :row-count="rowCount"
        :query="tableQuery"
        :manual="useServerModel"
        :global-filter="tableSearch"
        :loading="isPageLoading"
        @update:query="handleTableQueryChange"
      />

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
          <p class="text-xs mt-1" style="color: var(--color-text-muted);">Try refreshing the workspace</p>
        </div>
      </div>

      <!-- Empty state: no artifacts at all -->
      <TableEmptyState
        v-else
        title="No saved tables"
        subtitle="Ask AI for a table, or promote one from Runs."
      >
        <template #icon>
          <TableCellsIcon class="h-12 w-12 mx-auto mb-3" style="color: var(--color-border);" />
        </template>
      </TableEmptyState>
    </TableGridShell>
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
  <FloatingActionMenu
    :is-open="tableActionsOpen"
    :position="tableActionsPosition"
    :items="tableActionItems"
    width-class="w-44"
    :width="176"
    :height="56"
    @select="handleTableAction"
    @close="tableActionsOpen = false"
  />
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useAppCoordinatorStore } from '../../stores/appCoordinatorStore'
import apiService from '../../services/apiRuntime'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import DataTable from './table/DataTable.vue'
import TableEmptyState from './table/TableEmptyState.vue'
import TableGridShell from './table/TableGridShell.vue'
import TableToolbar from './table/TableToolbar.vue'
import FloatingActionMenu from '../ui/FloatingActionMenu.vue'
import { toast } from '../../composables/useToast'
import { persistExportFile } from '../../utils/exportFile'
import { useTableArtifacts } from '../../composables/useTableArtifacts'
import {
  createTableQuery,
  DEFAULT_TABLE_PAGE_SIZE,
  toBackendFilterModel,
  toBackendSortModel,
} from './table/tableQuery'
import {
  ArrowDownTrayIcon,
  EllipsisHorizontalIcon,
  FunnelIcon,
  TableCellsIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppCoordinatorStore()
useTableArtifacts()

const pageSize = DEFAULT_TABLE_PAGE_SIZE
const isDownloading = ref(false)
const isDeletingArtifact = ref(false)
const isDeleteDialogOpen = ref(false)
const tableActionsOpen = ref(false)
const tableActionsButtonRef = ref(null)
const tableActionsPosition = ref({ x: 0, y: 0 })
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
const tableQuery = ref(createTableQuery({ pageSize }))
const tableError = ref('')
const artifactListError = ref('')
const pendingControllers = new Set()
let listAbortController = null
let serializedRequestQueue = Promise.resolve()
let selectedArtifactLoadToken = 0
let currentPageRequestToken = 0
let tableSearchDebounceTimer = null
const pendingRestorePageByArtifact = new Map()
const tableActionItems = computed(() => [
  { id: 'delete', label: 'Delete table', destructive: true, disabled: !canDeleteSelectedArtifact.value || isDeletingArtifact.value },
])

function toggleTableActions() {
  const rect = tableActionsButtonRef.value?.getBoundingClientRect?.()
  if (rect) tableActionsPosition.value = { x: rect.right - 176, y: rect.bottom + 8 }
  tableActionsOpen.value = !tableActionsOpen.value
}

function handleTableAction(action) {
  if (action === 'delete') openDeleteDialog()
}

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
})

const allArtifacts = computed(() => (Array.isArray(workspaceArtifacts.value) ? workspaceArtifacts.value : []))

function normalizeClientRowsFromDataframeValue(value) {
  if (Array.isArray(value)) {
    return value
      .filter((row) => row && typeof row === 'object' && !Array.isArray(row))
      .map((row) => ({ ...row }))
  }
  if (!value || typeof value !== 'object') return []

  const rawRows = Array.isArray(value.data) ? value.data : []
  if (!rawRows.length) return []
  if (rawRows[0] && typeof rawRows[0] === 'object' && !Array.isArray(rawRows[0])) {
    return rawRows.map((row) => ({ ...row }))
  }

  const columns = Array.isArray(value.columns) ? value.columns.map((column) => String(column)) : []
  if (!columns.length) return []
  return rawRows
    .map((row) => {
      if (!Array.isArray(row)) return null
      const mapped = {}
      columns.forEach((column, idx) => {
        mapped[column] = row[idx]
      })
      return mapped
    })
    .filter(Boolean)
}

function normalizeLiveDataframeArtifact(item, index) {
  const data = item?.data && typeof item.data === 'object' ? item.data : item
  const rows = normalizeClientRowsFromDataframeValue(data)
  const columns = Array.isArray(data?.columns) && data.columns.length > 0
    ? data.columns.map((column) => String(column))
    : (rows[0] ? Object.keys(rows[0]) : [])
  const artifactId = String(data?.artifact_id || item?.artifact_id || `live-dataframe-${index + 1}`).trim()
  const logicalName = String(data?.logical_name || item?.logical_name || item?.name || `dataframe_${index + 1}`).trim()
  return {
    artifact_id: artifactId,
    logical_name: logicalName,
    display_name: String(data?.display_name || item?.display_name || logicalName).trim(),
    row_count: Number(data?.row_count || rows.length || 0),
    schema: columns.map((name) => ({ name })),
    preview_rows: rows,
    source: item?.promoted ? 'revision' : 'live',
  }
}

const liveDataframeArtifacts = computed(() => {
  const persistedIds = new Set(
    allArtifacts.value
      .map((artifact) => String(artifact?.artifact_id || '').trim())
      .filter(Boolean),
  )
  const conversationId = String(appStore.activeConversationId || '').trim()
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const scopeKey = conversationId ? `conversation:${conversationId}` : `workspace:${workspaceId || 'unscoped'}`
  const userRevisions = (Array.isArray(appStore.promotedUserDataframes) ? appStore.promotedUserDataframes : [])
    .filter((item) => String(item?.scopeKey || '') === scopeKey)
  return [...userRevisions, ...(Array.isArray(appStore.dataframes) ? appStore.dataframes : [])]
    .map((item, index) => normalizeLiveDataframeArtifact(item, index))
    .filter((artifact) => artifact.artifact_id && !persistedIds.has(artifact.artifact_id))
})

const displayArtifacts = computed(() => {
  const persistedArtifacts = allArtifacts.value.map((artifact) => ({
    ...artifact,
    source: 'artifact',
  }))
  return [...liveDataframeArtifacts.value, ...persistedArtifacts]
})

const tableDropdownOptions = computed(() => displayArtifacts.value.map((artifact, index) => ({
  value: artifact.artifact_id,
  label: artifact.display_name || artifact.logical_name || `Table ${index + 1}`,
  key: artifact.artifact_id,
})))

const showArtifactListLoadingState = computed(() => {
  return isLoadingArtifacts.value && Boolean(String(appStore.activeTurnId || '').trim())
})

// Expose dataframe count to the store so StatusBar can read it
watch(allArtifacts, () => {
  if (
    selectedArtifactId.value
    && !displayArtifacts.value.some((item) => item.artifact_id === selectedArtifactId.value)
  ) {
    selectedArtifactId.value = null
  }
}, { immediate: true })

watch(displayArtifacts, (list) => {
  appStore.setDataframeCount(list.length)
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const preferredArtifactId = workspaceId ? appStore.getSelectedTableArtifact(workspaceId) : ''
  if (
    preferredArtifactId
    && preferredArtifactId !== selectedArtifactId.value
    && list.some((item) => item.artifact_id === preferredArtifactId)
  ) {
    selectedArtifactId.value = preferredArtifactId
    return
  }
  if (!selectedArtifactId.value && list.length > 0) {
    selectedArtifactId.value = list[0]?.artifact_id || null
    return
  }
  if (selectedArtifactId.value && !list.some((item) => item.artifact_id === selectedArtifactId.value)) {
    selectedArtifactId.value = null
  }
}, { immediate: true })

watch(
  () => appStore.getSelectedTableArtifact(appStore.activeWorkspaceId),
  (preferredArtifactId) => {
    const normalizedArtifactId = String(preferredArtifactId || '').trim()
    if (
      normalizedArtifactId
      && normalizedArtifactId !== String(selectedArtifactId.value || '').trim()
      && displayArtifacts.value.some((item) => String(item?.artifact_id || '').trim() === normalizedArtifactId)
    ) {
      selectedArtifactId.value = normalizedArtifactId
    }
  },
)

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

function isArtifactMissingError(error) {
  const status = Number(error?.response?.status ?? error?.status ?? 0)
  if (status === 404) return true
  const detail = String(error?.response?.data?.detail || error?.message || '').toLowerCase()
  return detail.includes('artifact not found')
}

function clearMissingSelectedArtifact(artifactId) {
  const normalizedArtifactId = String(artifactId || selectedArtifactId.value || '').trim()
  if (!normalizedArtifactId) return
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (workspaceId && String(appStore.getSelectedTableArtifact(workspaceId) || '').trim() === normalizedArtifactId) {
    appStore.setSelectedTableArtifact(workspaceId, '')
  }
  if (String(selectedArtifactId.value || '').trim() === normalizedArtifactId) {
    selectedArtifactId.value = null
  }
  workspaceArtifacts.value = workspaceArtifacts.value.filter(
    (artifact) => String(artifact?.artifact_id || '').trim() !== normalizedArtifactId,
  )
  appStore.removeResultArtifact(normalizedArtifactId)
  resetTableState()
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
    selectedArtifactId.value = liveDataframeArtifacts.value[0]?.artifact_id || null
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
    const liveArtifact = liveDataframeArtifacts.value.find(
      (entry) => String(entry?.artifact_id || '').trim() === String(newId || '').trim(),
    )
    if (!liveArtifact) {
      tableError.value = 'Selected table is not available for this turn.'
      return
    }
    const rows = normalizeClientRowsFromDataframeValue({
      columns: Array.isArray(liveArtifact.schema) ? liveArtifact.schema.map((column) => column?.name).filter(Boolean) : [],
      data: liveArtifact.preview_rows,
      row_count: liveArtifact.row_count,
    })
    useClientFallback.value = true
    clientRows.value = rows
    serverRows.value = rows
    serverColumns.value = rows[0]
      ? Object.keys(rows[0])
      : (Array.isArray(liveArtifact.schema) ? liveArtifact.schema.map((column) => String(column?.name || '')).filter(Boolean) : [])
    rowCountValue.value = Number(liveArtifact.row_count || rows.length || 0)
    windowStart.value = rows.length > 0 ? 1 : 0
    windowEnd.value = rows.length > 0 ? Math.min(pageSize, rowCountValue.value || rows.length) : 0
    appStore.setTableViewport(windowStart.value, windowEnd.value, rowCountValue.value)
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
    tableQuery.value = createTableQuery({
      ...tableQuery.value,
      pageIndex: 0,
    })
    if (!useServerModel.value) {
      updateTableViewport()
      return
    }
    void loadServerPage(artifactId, tableQuery.value)
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

const useServerModel = computed(() => {
  return !!selectedArtifactId.value && !useClientFallback.value
})

const rowCount = computed(() => {
  if (useServerModel.value) return Number(rowCountValue.value || 0)
  return Number(clientRows.value.length || 0)
})

const downloadRows = computed(() => {
  if (useServerModel.value) return Array.isArray(serverRows.value) ? serverRows.value : []
  return Array.isArray(clientRows.value) ? clientRows.value : []
})

const hasRenderableRows = computed(() => {
  if (useServerModel.value) return rowCount.value > 0 || serverColumns.value.length > 0
  return clientRows.value.length > 0 || serverColumns.value.length > 0
})

const visibleTableRows = computed(() => (
  useServerModel.value ? serverRows.value : clientRows.value
))

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

const tableColumns = computed(() => {
  if (serverColumns.value.length > 0) {
    return serverColumns.value.map((name) => String(name))
  }
  const sourceRows = downloadRows.value
  if (!sourceRows || sourceRows.length === 0) return []
  return Object.keys(sourceRows[0] || {})
})

function cancelPendingRequests() {
  for (const controller of pendingControllers) {
    try { controller.abort() } catch (_) { /* no-op */ }
  }
  pendingControllers.clear()
}

function resetTableState() {
  currentPageRequestToken += 1
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
  tableQuery.value = createTableQuery({ pageSize })
}

function updateTableViewport() {
  const total = rowCount.value
  if (total <= 0) {
    windowStart.value = 0
    windowEnd.value = 0
    appStore.clearTableViewport()
    return
  }
  const page = Math.max(0, Number(tableQuery.value.pageIndex || 0))
  const aid = selectedArtifactId.value
  if (aid) {
    pendingRestorePageByArtifact.delete(aid)
    appStore.setTablePageOffset(appStore.activeWorkspaceId, aid, page)
  }
  const start = page * pageSize + 1
  const visibleLength = useServerModel.value ? serverRows.value.length : pageSize
  const end = Math.min(total, start + Math.max(0, visibleLength) - 1)
  windowStart.value = start
  windowEnd.value = end
  appStore.setTableViewport(start, end, total)
}

function restoredArtifactPage(artifactId) {
  if (!artifactId || String(tableSearch.value || '').trim()) return 0
  const rememberedPage = pendingRestorePageByArtifact.get(artifactId)
    ?? appStore.getTablePageOffset(appStore.activeWorkspaceId, artifactId)
  if (!Number.isInteger(rememberedPage) || rememberedPage <= 0) return 0
  const knownTotal = Number(selectedArtifactMeta.value?.row_count || 0)
  if (knownTotal <= 0) return rememberedPage
  return Math.min(rememberedPage, Math.max(0, Math.ceil(knownTotal / pageSize) - 1))
}

function handleTableQueryChange(nextQuery) {
  const normalizedQuery = createTableQuery(nextQuery)
  tableQuery.value = normalizedQuery
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!artifactId) return
  appStore.setTablePageOffset(appStore.activeWorkspaceId, artifactId, normalizedQuery.pageIndex)
  if (useServerModel.value) {
    void loadServerPage(artifactId, normalizedQuery)
    return
  }
  updateTableViewport()
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
  clientRows.value = []
  const pageIndex = restoredArtifactPage(artifactId)
  tableQuery.value = createTableQuery({ pageIndex, pageSize })
  await loadServerPage(artifactId, tableQuery.value)
}

async function loadServerPage(artifactId, query = tableQuery.value) {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const conversationId = String(appStore.activeConversationId || '').trim()
  const turnId = String(appStore.activeTurnId || '').trim()
  const normalizedArtifactId = String(artifactId || '').trim()
  if (!workspaceId || !normalizedArtifactId || !conversationId || !turnId) return

  cancelPendingRequests()
  const requestToken = ++currentPageRequestToken
  isPageLoading.value = true
  tableError.value = ''
  const controller = new AbortController()
  pendingControllers.add(controller)
  try {
    const pageIndex = Math.max(0, Number(query?.pageIndex || 0))
    const requestLimit = Math.max(1, Math.min(pageSize, Number(query?.pageSize || pageSize)))
    const startRow = pageIndex * requestLimit
    const payload = await enqueueSerializedRequest(async () => {
      if (workspaceId !== String(appStore.activeWorkspaceId || '').trim()) throw createAbortError()
      if (conversationId !== String(appStore.activeConversationId || '').trim()) throw createAbortError()
      if (turnId !== String(appStore.activeTurnId || '').trim()) throw createAbortError()
      if (normalizedArtifactId !== String(selectedArtifactId.value || '').trim()) throw createAbortError()
      return apiService.getTurnDataframeArtifactRows(
        conversationId,
        turnId,
        normalizedArtifactId,
        startRow,
        requestLimit,
        {
          signal: controller.signal,
          sortModel: toBackendSortModel(query),
          filterModel: toBackendFilterModel(query),
          searchText: String(tableSearch.value || '').trim(),
        },
      )
    })
    if (requestToken !== currentPageRequestToken) return
    const rows = Array.isArray(payload?.rows) ? payload.rows : []
    const nextColumns = Array.isArray(payload?.columns)
      ? payload.columns.map((c) => String(c))
      : (rows[0] ? Object.keys(rows[0]) : [])
    if (columnsChanged(nextColumns)) {
      serverColumns.value = nextColumns
    }
    const nextRowCount = Number(payload?.row_count ?? rows.length ?? 0)
    const maxPage = Math.max(0, Math.ceil(nextRowCount / requestLimit) - 1)
    if (pageIndex > maxPage) {
      const clampedQuery = createTableQuery({ ...query, pageIndex: maxPage })
      tableQuery.value = clampedQuery
      appStore.setTablePageOffset(workspaceId, normalizedArtifactId, maxPage)
      pendingControllers.delete(controller)
      if (requestToken === currentPageRequestToken) isPageLoading.value = false
      await loadServerPage(normalizedArtifactId, clampedQuery)
      return
    }
    serverRows.value = rows
    rowCountValue.value = nextRowCount
    tableQuery.value = createTableQuery(query)
    updateTableViewport()
  } catch (error) {
    if (isAbortError(error)) return
    if (isArtifactMissingError(error)) {
      clearMissingSelectedArtifact(normalizedArtifactId)
      return
    }
    if (requestToken !== currentPageRequestToken) return
    console.error('Failed to load dataframe page:', error)
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
    if (requestToken === currentPageRequestToken) {
      isPageLoading.value = false
    }
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
    appStore.removeResultArtifact(artifactId)
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
.table-pane-surface {
  background-color: var(--color-base);
}
</style>
