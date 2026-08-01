<template>
  <div class="schema-editor h-full flex flex-col relative overflow-hidden bg-[var(--color-base)] text-[var(--color-text-main)] font-sans">
    <!-- Header -->
    <div class="schema-top-bar relative z-10 border-b border-[var(--color-border)] p-4 flex flex-wrap items-center justify-between gap-3 bg-[var(--color-surface)]">
      <div>
        <h2 class="text-[15px] font-semibold leading-tight">Workspace data</h2>
        <p class="mt-1 text-[13px] text-[var(--color-text-muted)]">Manage context, sources, schemas, and table previews.</p>
      </div>
      <div class="flex items-center gap-2">
        <button type="button" @click="refreshWorkspaceSchema" :disabled="schemaBusy || schemaHub.isEdited.value" :title="schemaHub.isEdited.value ? 'Save or discard table changes before refreshing' : 'Refresh data sources and reload schema'" class="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] disabled:opacity-50">
          <span v-if="isRefreshingSources" class="inquira-spinner h-3.5 w-3.5 border-2" aria-hidden="true"></span>
          <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M20 11a8.1 8.1 0 00-15.5-2M4 4v5h5m-5 4a8.1 8.1 0 0015.5 2M20 20v-5h-5"></path></svg>
          {{ isRefreshingSources ? 'Refreshing…' : 'Refresh' }}
        </button>
        <button
          type="button"
          class="btn-primary flex items-center gap-1.5 px-3 py-1.5 text-[13px]"
          :disabled="schemaBusy || schemaHub.isEdited.value"
          :title="schemaHub.isEdited.value ? 'Save or discard table changes before adding data' : 'Add data to this workspace'"
          data-action="add-workspace-data"
          @click="requestAddData"
        >
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          Add data
        </button>
      </div>
    </div>

    <!-- Empty State for No Workspace -->
    <div v-if="!hasWorkspace" class="flex flex-1 flex-col items-center justify-center py-16">
      <div class="relative mb-6">
        <div class="flex h-20 w-20 items-center justify-center rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm">
          <svg class="w-10 h-10 text-[var(--color-text-muted)] opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
        </div>
      </div>
      <h3 class="text-lg font-semibold mb-2 text-[var(--color-text-main)]">No Active Workspace</h3>
      <p class="text-sm text-[var(--color-text-muted)]">Select or create a workspace to view and edit schema.</p>
    </div>

    <!-- Content Area -->
    <div v-else class="flex flex-1 overflow-hidden">
      <SchemaTableNavigator
        :tables="groupedSchema"
        :selection="schemaHub.selection.value"
        :dirty-table-ids="schemaHub.dirtyTableIds.value"
        :source-count="sourceCount"
        @select="requestSchemaSelection"
      />

      <main class="min-w-0 flex-1 overflow-auto schema-scroll-area">
        <div v-if="schemaHub.isLoading.value" class="flex h-40 flex-col items-center justify-center">
          <div class="relative w-10 h-10 mb-3">
            <div class="absolute inset-0 rounded-full border-2 border-[var(--color-border)] opacity-30"></div>
            <div class="inquira-spinner absolute inset-0 border-2 border-r-transparent border-b-transparent border-l-transparent"></div>
          </div>
          <p class="text-sm font-medium text-[var(--color-text-muted)]">Loading workspace schema...</p>
        </div>
        <WorkspaceContextSurface
          v-show="!schemaHub.isLoading.value && schemaHub.selection.value.kind === 'workspace'"
          :key="workspaceStore.activeWorkspaceId"
          v-model="schemaContext"
          :save-context="saveWorkspaceContext"
        />
        <WorkspaceDataSources
          v-show="!schemaHub.isLoading.value && schemaHub.selection.value.kind === 'sources'"
          ref="dataSourcesRef"
          :workspace-id="workspaceStore.activeWorkspaceId"
          @changed="handleSourcesChanged"
          @update:count="sourceCount = $event"
        />
        <div v-if="!schemaHub.isLoading.value && schemaHub.selectedTable.value" class="flex min-h-full flex-col gap-4 p-4 pb-6">
          <div class="flex shrink-0 items-center justify-between gap-3">
            <button
              type="button"
              class="rounded-md px-2.5 py-1.5 text-[12px] font-medium text-[var(--color-danger)] transition-colors hover:bg-[var(--color-danger-bg)] disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="schemaBusy || schemaHub.isEdited.value"
              :title="schemaHub.isEdited.value ? 'Save or discard table changes before removing this dataset' : `Remove ${schemaHub.selectedTable.value.tableName}`"
              @click="pendingDatasetRemoval = schemaHub.selectedTable.value"
            >
              Remove dataset
            </button>
            <SegmentedControl v-model="tableView" :options="tableViewOptions" aria-label="Table details" />
          </div>
          <template v-if="tableView === 'schema'">
            <TableContextSurface
              :key="schemaHub.selectedTable.value.id"
              :model-value="schemaHub.selectedTable.value.tableContext || ''"
              :table-name="schemaHub.selectedTable.value.tableName"
              :save-context="(context) => saveTableContext(schemaHub.selectedTable.value!.id, context)"
              @update:model-value="schemaHub.replaceTableContext(schemaHub.selectedTable.value!.id, $event)"
            />
            <TableMetadataSurface
              :table="schemaHub.selectedTable.value"
              :dirty="schemaHub.dirtyTableIds.value.has(schemaHub.selectedTable.value.id)"
              :saving="savingTableId === schemaHub.selectedTable.value.id"
              :regenerating="regeneratingTableName === schemaHub.selectedTable.value.tableName"
              :busy="schemaBusy || Boolean(regeneratingTableName)"
              @change="handleTableColumnsChange"
              @save="saveTableSchema"
              @regenerate="regenerateTableSchema"
            />
          </template>
          <TableDataPreview
            v-else
            :key="`${schemaHub.selectedTable.value.id}:${previewRevision}`"
            :workspace-id="workspaceStore.activeWorkspaceId"
            :table="schemaHub.selectedTable.value"
          />
        </div>
      </main>
    </div>

    <ConfirmationModal
      :is-open="Boolean(pendingSelection)"
      title="Discard unsaved changes?"
      :message="`Changes to ${schemaHub.selectedTable.value?.tableName || 'this table'} have not been saved.`"
      confirm-text="Discard and switch"
      @close="pendingSelection = null"
      @confirm="discardAndSelect"
    />
    <ConfirmationModal
      :is-open="Boolean(pendingDatasetRemoval)"
      title="Remove dataset?"
      :message="`This removes ${pendingDatasetRemoval?.tableName || 'this dataset'} and its local snapshot from this workspace. Other datasets from the same source will stay connected. This cannot be undone.`"
      confirm-text="Remove"
      @close="pendingDatasetRemoval = null"
      @confirm="removeSelectedDataset"
    />
  </div>
</template>

<script lang="ts">
const handledWorkspaceDataRequestIds = new WeakMap<object, number>()
</script>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { workspaceApi } from '../../api/workspaces'
import { useExecutionStore } from '../../stores/executionStore'
import { useUiStore } from '../../stores/uiStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import TableMetadataSurface from '../schema/TableMetadataSurface.vue'
import TableContextSurface from '../schema/TableContextSurface.vue'
import TableDataPreview from '../schema/TableDataPreview.vue'
import SchemaTableNavigator from '../schema/SchemaTableNavigator.vue'
import WorkspaceContextSurface from '../schema/WorkspaceContextSurface.vue'
import WorkspaceDataSources from '../schema/WorkspaceDataSources.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import {
  normalizeSchemaColumns,
  normalizeSchemaTables,
  useSchemaHubState,
} from '../../composables/useSchemaHubState'
import { toast } from '../../composables/useToast'
import { clearDatasetPreviewCache } from '../../composables/useDatasetPreview'
import type { SchemaHubColumn, SchemaHubSelection, SchemaHubTable } from '../../types/schemaHub'
import { normalizeSchemaRefreshResult, schemaRefreshFeedback } from '../../utils/schemaRefresh'

const executionStore = useExecutionStore()
const uiStore = useUiStore()
const workspaceStore = useWorkspaceStore()

const schemaHub = useSchemaHubState()
const savingTableId = ref('')
const savingTableContextId = ref('')
const isRefreshingSources = ref(false)
const removingDataset = ref(false)
const schemaBusy = computed(() => schemaHub.isLoading.value || isRefreshingSources.value || removingDataset.value || Boolean(savingTableId.value) || Boolean(savingTableContextId.value))
const regeneratingTableName = ref('')
const pendingSelection = ref<SchemaHubSelection | null>(null)
const pendingDatasetRemoval = ref<SchemaHubTable | null>(null)
const groupedSchema = schemaHub.tables
const dataSourcesRef = ref<InstanceType<typeof WorkspaceDataSources> | null>(null)
const sourceCount = ref(0)
const tableView = ref('schema')
const previewRevision = ref(0)
const tableViewOptions = [
  { value: 'schema', label: 'Schema' },
  { value: 'preview', label: 'Preview' },
]

const schemaContext = ref('')

const hasWorkspace = computed(() => !!workspaceStore.activeWorkspaceId)

function requestSchemaSelection(selection: SchemaHubSelection) {
  const currentSelection = schemaHub.selection.value
  const isCurrent = selection.kind === currentSelection.kind
    && (selection.kind !== 'table' || (currentSelection.kind === 'table' && selection.tableId === currentSelection.tableId))
  if (isCurrent) return
  const currentTable = schemaHub.selectedTable.value
  if (currentTable && schemaHub.dirtyTableIds.value.has(currentTable.id)) {
    pendingSelection.value = selection
    return
  }
  applySchemaSelection(selection)
}

function applySchemaSelection(selection: SchemaHubSelection) {
  if (selection.kind === 'workspace') schemaHub.selectWorkspace()
  else if (selection.kind === 'sources') schemaHub.selectSources()
  else schemaHub.selectTable(selection.tableId)
}

async function requestAddData() {
  if (!hasWorkspace.value || schemaBusy.value || schemaHub.isEdited.value) return
  requestSchemaSelection({ kind: 'sources' })
  await nextTick()
  await dataSourcesRef.value?.chooseFile()
}

async function handleRequestedAddData() {
  const requestId = Math.max(0, Math.floor(Number(uiStore.connectionFlowRequestId || 0)))
  const lastHandledRequestId = Number(handledWorkspaceDataRequestIds.get(workspaceStore) || 0)
  if (!requestId || requestId <= lastHandledRequestId) return
  if (!hasWorkspace.value || schemaBusy.value || schemaHub.isEdited.value || !dataSourcesRef.value) return

  handledWorkspaceDataRequestIds.set(workspaceStore, requestId)
  await requestAddData()
}

async function handleSourcesChanged() {
  clearDatasetPreviewCache(workspaceStore.activeWorkspaceId)
  previewRevision.value += 1
  await fetchWorkspaceSchema()
  await workspaceStore.fetchWorkspaceSummary(workspaceStore.activeWorkspaceId)
  await workspaceStore.fetchColumnCatalog({ force: true })
}

async function removeSelectedDataset() {
  const workspaceId = workspaceStore.activeWorkspaceId
  const table = pendingDatasetRemoval.value
  pendingDatasetRemoval.value = null
  if (!workspaceId || !table || removingDataset.value || schemaHub.isEdited.value) return
  removingDataset.value = true
  try {
    await workspaceApi.removeDataset(workspaceId, table.tableName)
    if (workspaceStore.activeWorkspaceId !== workspaceId) return
    clearDatasetPreviewCache(workspaceId)
    previewRevision.value += 1
    schemaHub.selectSources()
    await Promise.all([
      fetchWorkspaceSchema(),
      dataSourcesRef.value?.reload(),
      workspaceStore.fetchWorkspaceSummary(workspaceId),
      workspaceStore.fetchColumnCatalog({ force: true }),
    ])
    toast.success('Dataset removed', `${table.tableName} was removed from this workspace.`)
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId === workspaceId) {
      toast.error('Could not remove dataset', error?.message || 'The dataset could not be removed.')
    }
  } finally {
    removingDataset.value = false
  }
}

function discardAndSelect() {
  const selection = pendingSelection.value
  const currentTable = schemaHub.selectedTable.value
  if (!selection) return
  if (currentTable) schemaHub.resetTable(currentTable.id)
  pendingSelection.value = null
  applySchemaSelection(selection)
}

async function loadWorkspaceContext() {
  const workspaceId = workspaceStore.activeWorkspaceId
  if (!workspaceId) {
    schemaContext.value = ''
    return
  }
  try {
    const summary = await workspaceApi.summary(workspaceId)
    if (workspaceStore.activeWorkspaceId !== workspaceId) return
    schemaContext.value = String(summary?.schema_context || '').trim()
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId !== workspaceId) return
    // Silently fail or use store fallback
    schemaContext.value = String(workspaceStore.workspaces.find((w: any) => w.id === workspaceId)?.schema_context || '').trim()
  }
}

async function fetchWorkspaceSchema() {
  if (!workspaceStore.activeWorkspaceId) return false
  const loadId = schemaHub.beginLoad()
  try {
    const workspaceId = workspaceStore.activeWorkspaceId
    const datasetResponse: any = await workspaceApi.listDatasets(workspaceId)
    const datasets = datasetResponse?.datasets || []

    const schemas = await Promise.all(
      datasets.map(async (ds: any) => {
        try {
          return await workspaceApi.getDatasetSchema(workspaceId, ds.table_name)
        } catch (err) {
          return { table_name: ds.table_name, context: '', columns: [] }
        }
      })
    )

    return schemaHub.applyLoad(loadId, normalizeSchemaTables(datasets, schemas))
  } catch (error: any) {
    if (schemaHub.rejectLoad(loadId, error)) {
      toast.error('Failed to load schema', error?.message || 'Unknown error occurred.')
    }
    return false
  }
}

async function refreshWorkspaceSchema() {
  const workspaceId = workspaceStore.activeWorkspaceId
  if (!workspaceId || schemaBusy.value || schemaHub.isEdited.value) return
  isRefreshingSources.value = true
  try {
    const result = normalizeSchemaRefreshResult(await workspaceApi.refreshDatasetSources(workspaceId))
    if (workspaceStore.activeWorkspaceId !== workspaceId) return
    clearDatasetPreviewCache(workspaceId)
    previewRevision.value += 1
    if (!await fetchWorkspaceSchema() || workspaceStore.activeWorkspaceId !== workspaceId) return
    const feedback = schemaRefreshFeedback(result)
    toast[feedback.type](feedback.title, feedback.message)
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId === workspaceId) {
      toast.error('Schema refresh failed', error?.message || 'Unable to refresh workspace data sources.')
    }
  } finally {
    isRefreshingSources.value = false
  }
}

async function saveWorkspaceContext(context: string) {
  const workspaceId = workspaceStore.activeWorkspaceId
  if (!workspaceId) throw new Error('Select a workspace before saving context.')
  try {
    const workspace = workspaceStore.workspaces.find((w: any) => w.id === workspaceId)
    await workspaceApi.update(workspaceId, workspace?.name ?? null, context)
    if (workspaceStore.activeWorkspaceId !== workspaceId) {
      throw new DOMException('Workspace changed before the context save completed.', 'AbortError')
    }
    toast.success('Workspace context saved')
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId === workspaceId) {
      toast.error('Failed to save context', error?.message)
    }
    throw error
  }
}

function handleTableColumnsChange(tableId: string, columns: SchemaHubColumn[]) {
  schemaHub.replaceTableColumns(tableId, columns)
  schemaHub.markTableDirty(tableId)
}

async function saveTableContext(tableId: string, context: string) {
  const workspaceId = workspaceStore.activeWorkspaceId
  const table = groupedSchema.value.find((candidate) => candidate.id === tableId)
  if (!workspaceId || !table || savingTableContextId.value) return
  savingTableContextId.value = tableId
  try {
    await workspaceApi.saveDatasetContext(workspaceId, table.tableName, context)
    if (workspaceStore.activeWorkspaceId !== workspaceId) {
      throw new DOMException('Workspace changed before the table context save completed.', 'AbortError')
    }
    toast.success('Table context saved', `Saved context for ${table.tableName}.`)
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId === workspaceId) {
      toast.error('Failed to save table context', error?.message)
    }
    throw error
  } finally {
    savingTableContextId.value = ''
  }
}

async function saveTableSchema(tableId: string, columns: SchemaHubColumn[]) {
  const workspaceId = workspaceStore.activeWorkspaceId
  const table = groupedSchema.value.find((candidate) => candidate.id === tableId)
  if (!workspaceId || !table || savingTableId.value) return
  handleTableColumnsChange(tableId, columns)
  savingTableId.value = tableId
  try {
    await workspaceApi.saveDatasetSchema(workspaceId, table.tableName, {
      context: schemaContext.value || '',
      columns: columns.map((column) => ({
        name: column.name,
        dtype: column.dataType || 'VARCHAR',
        description: column.description || '',
        aliases: column.aliases || [],
      })),
    })
    if (workspaceStore.activeWorkspaceId === workspaceId) {
      schemaHub.clearTableDirty(tableId)
      toast.success('Table schema saved', `Saved metadata for ${table.tableName}.`)
    }
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId === workspaceId) {
      toast.error('Failed to save table schema', error?.message)
    }
  } finally {
    savingTableId.value = ''
  }
}


async function regenerateTableSchema(tableName: string) {
  if (!workspaceStore.activeWorkspaceId || !tableName) return
  if (regeneratingTableName.value) return
  regeneratingTableName.value = tableName
  const operationId = executionStore.startBackgroundOperation({
    id: `schema-regeneration-${tableName}`,
    type: 'schema',
    title: 'Regenerating schema',
    message: `Generating schema for ${tableName}...`,
    priority: 75,
  })
  try {
    toast.info('Regenerating table schema', `Generating AI descriptions for ${tableName}...`)
    const regenerated: any = await workspaceApi.regenerateDatasetSchema(workspaceStore.activeWorkspaceId, tableName, {
      context: schemaContext.value || ''
    })

    const table = groupedSchema.value.find((candidate) => candidate.tableName === tableName)
    if (table) {
      schemaHub.replaceTableColumns(
        table.id,
        normalizeSchemaColumns(table.id, tableName, regenerated.columns),
      )
      schemaHub.clearTableDirty(table.id)
    }
    executionStore.finishBackgroundOperation(operationId, {
      title: 'Schema regenerated',
      message: `Schema updated for ${tableName}.`,
    })
    toast.success('Table schema regenerated', `AI descriptions updated for ${tableName}.`)
  } catch (error: any) {
    executionStore.finishBackgroundOperation(operationId, {
      status: 'failed',
      title: 'Schema regeneration failed',
      message: error?.message || 'Unable to regenerate schema.',
    })
    toast.error('Regeneration failed', error?.message || 'Unable to regenerate schema.')
  } finally {
    regeneratingTableName.value = ''
  }
}

async function handleDatasetSchemaReady(event: any) {
  await fetchWorkspaceSchema()
}

onMounted(async () => {
  await loadWorkspaceContext()
  await fetchWorkspaceSchema()
  window.addEventListener('dataset-schema-ready', handleDatasetSchemaReady)
  await handleRequestedAddData()
})

onUnmounted(() => {
  window.removeEventListener('dataset-schema-ready', handleDatasetSchemaReady)
})

watch(() => workspaceStore.activeWorkspaceId, async (newId) => {
  pendingSelection.value = null
  schemaHub.clear()
  if (newId) {
    await loadWorkspaceContext()
    await fetchWorkspaceSchema()
  } else {
    schemaContext.value = ''
  }
})

watch(
  [
    () => Number(uiStore.connectionFlowRequestId || 0),
    () => hasWorkspace.value,
    () => schemaBusy.value,
    () => schemaHub.isEdited.value,
    () => dataSourcesRef.value,
  ],
  () => { void handleRequestedAddData() },
  { flush: 'post' },
)

</script>

<style scoped>
.schema-scroll-area {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.schema-scroll-area::-webkit-scrollbar {
  width: 0;
  height: 0;
}

</style>
