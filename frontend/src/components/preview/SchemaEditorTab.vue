<template>
  <div class="schema-editor relative flex h-full flex-col overflow-hidden bg-[var(--color-base)] font-sans text-[var(--color-text-main)]">
    <header class="schema-top-bar relative z-10 shrink-0 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 pt-4">
      <div class="flex flex-wrap items-center justify-between gap-4 pb-3">
        <div class="min-w-0">
          <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Workspace</p>
          <h2 class="mt-1 truncate text-[15px] font-semibold leading-tight tracking-tight">{{ activeWorkspaceName }}</h2>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="activeWorkspaceSection === 'data'"
            type="button"
            class="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-50"
            :disabled="!hasWorkspace || schemaBusy || schemaHub.isEdited.value"
            :title="schemaHub.isEdited.value ? 'Save or discard table changes before managing sources' : 'Manage workspace data sources'"
            data-action="manage-workspace-sources"
            @click="openSourceDrawer"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7"/></svg>
            Sources
            <span v-if="sourceCount" class="rounded-full bg-[var(--color-base-muted)] px-1.5 text-[10px] tabular-nums text-[var(--color-text-muted)]">{{ sourceCount }}</span>
          </button>
          <button
            v-if="activeWorkspaceSection === 'data'"
            type="button"
            class="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-50"
            :disabled="!hasWorkspace || schemaBusy || schemaHub.isEdited.value"
            :title="schemaHub.isEdited.value ? 'Save or discard table changes before refreshing' : 'Refresh data sources and reload schema'"
            @click="refreshWorkspaceSchema"
          >
            <span v-if="isRefreshingSources" class="inquira-spinner h-3.5 w-3.5 border-2" aria-hidden="true"></span>
            <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M20 11a8.1 8.1 0 00-15.5-2M4 4v5h5m-5 4a8.1 8.1 0 0015.5 2M20 20v-5h-5"></path></svg>
            {{ isRefreshingSources ? 'Refreshing…' : 'Refresh' }}
          </button>
          <button
            type="button"
            class="btn-primary flex items-center gap-1.5 px-3 py-1.5 text-[13px]"
            :disabled="!hasWorkspace || schemaBusy || schemaHub.isEdited.value"
            :title="schemaHub.isEdited.value ? 'Save or discard table changes before adding data' : 'Add data to this workspace'"
            data-action="add-workspace-data"
            @click="requestAddData"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            Add data
          </button>
        </div>
      </div>

      <nav class="flex gap-5" aria-label="Workspace manager sections" role="tablist">
        <button
          v-for="section in workspaceSections"
          :key="section.value"
          type="button"
          role="tab"
          class="relative -mb-px border-b-2 px-0.5 pb-2.5 pt-1 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
          :class="activeWorkspaceSection === section.value ? 'border-[var(--color-accent)] text-[var(--color-text-main)]' : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
          :aria-selected="activeWorkspaceSection === section.value"
          @click="openWorkspaceSection(section.value)"
        >
          {{ section.label }}
        </button>
      </nav>
    </header>

    <div v-if="!hasWorkspace" class="flex flex-1 flex-col items-center justify-center py-16 text-center">
      <div class="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-sm">
        <svg class="h-8 w-8 text-[var(--color-text-muted)] opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path></svg>
      </div>
      <h3 class="text-[15px] font-semibold">No active workspace</h3>
      <p class="mt-1 text-[13px] text-[var(--color-text-muted)]">Select or create a workspace to manage its data.</p>
    </div>

    <div v-else-if="activeWorkspaceSection === 'context'" class="schema-scroll-area min-h-0 flex-1 overflow-auto">
      <WorkspaceContextSurface
        :key="workspaceStore.activeWorkspaceId"
        v-model="schemaContext"
        :save-context="saveWorkspaceContext"
      />
    </div>

    <div v-else class="flex min-h-0 flex-1 overflow-hidden">
      <SchemaTableNavigator
        :tables="groupedSchema"
        :selection="schemaHub.selection.value"
        :dirty-table-ids="schemaHub.dirtyTableIds.value"
        @select="requestSchemaSelection"
      />

      <main class="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div v-if="schemaHub.isLoading.value" class="flex flex-1 flex-col items-center justify-center">
          <span class="inquira-spinner mb-3 h-5 w-5 border-2" aria-hidden="true"></span>
          <p class="text-[13px] font-medium text-[var(--color-text-muted)]">Loading workspace data…</p>
        </div>

        <div v-else-if="groupedSchema.length === 0" class="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <p class="text-[15px] font-medium text-[var(--color-text-main)]">No datasets found</p>
          <p class="mt-1 text-[13px] text-[var(--color-text-muted)]">Add a local data source to start exploring this workspace.</p>
          <button type="button" class="btn-primary mt-4 px-3 py-1.5 text-[13px]" @click="requestAddData">Add data</button>
        </div>

        <template v-else-if="schemaHub.selectedTable.value">
          <div class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
            <div class="min-w-0">
              <h3 class="truncate font-mono text-[14px] font-semibold text-[var(--color-text-main)]">{{ schemaHub.selectedTable.value.tableName }}</h3>
              <p class="mt-1 text-[11px] tabular-nums text-[var(--color-text-muted)]">
                {{ schemaHub.selectedTable.value.columns.length }} columns
                <span v-if="schemaHub.selectedTable.value.rowCount"> · {{ schemaHub.selectedTable.value.rowCount.toLocaleString() }} rows</span>
                <span v-if="schemaHub.selectedTable.value.status"> · {{ schemaHub.selectedTable.value.status }}</span>
              </p>
            </div>
            <div class="flex items-center gap-2">
              <SegmentedControl v-model="tableView" :options="tableViewOptions" aria-label="Dataset details" />
              <button
                type="button"
                class="flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-base-muted)] hover:text-[var(--color-text-main)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
                aria-label="Dataset actions"
                :aria-expanded="datasetMenuOpen"
                data-action="dataset-actions"
                @click="toggleDatasetActions"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>
              </button>
            </div>
          </div>

          <TableContextSurface
            :key="schemaHub.selectedTable.value.id"
            :model-value="schemaHub.selectedTable.value.tableContext || ''"
            :table-name="schemaHub.selectedTable.value.tableName"
            :save-context="(context) => saveTableContext(schemaHub.selectedTable.value!.id, context)"
            @update:model-value="schemaHub.replaceTableContext(schemaHub.selectedTable.value!.id, $event)"
          />

          <div v-if="tableView === 'schema'" class="schema-scroll-area min-h-0 flex-1 overflow-auto p-4 pb-8">
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
          </div>
          <TableDataPreview
            v-else
            :key="`${schemaHub.selectedTable.value.id}:${previewRevision}`"
            :workspace-id="workspaceStore.activeWorkspaceId"
            :table="schemaHub.selectedTable.value"
          />
        </template>
      </main>
    </div>

    <FloatingActionMenu
      :is-open="datasetMenuOpen"
      :position="datasetMenuPosition"
      :items="datasetMenuItems"
      :header="schemaHub.selectedTable.value?.tableName || ''"
      width-class="w-48"
      :width="192"
      :height="92"
      marker-attr="data-dataset-actions-menu"
      @close="datasetMenuOpen = false"
      @select="handleDatasetAction"
    />

    <div
      v-show="sourceDrawerOpen"
      class="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-[1px]"
      data-source-drawer-backdrop
      @pointerdown.self="closeSourceDrawer"
    >
      <aside class="h-full w-full max-w-[34rem] bg-[var(--color-surface)] shadow-2xl" role="dialog" aria-modal="true" aria-label="Workspace data sources">
        <WorkspaceDataSources
          v-if="hasWorkspace"
          ref="dataSourcesRef"
          :workspace-id="workspaceStore.activeWorkspaceId"
          @changed="handleSourcesChanged"
          @close="closeSourceDrawer"
          @update:count="sourceCount = $event"
        />
      </aside>
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { workspaceApi } from '../../api/workspaces'
import { clearDatasetPreviewCache } from '../../composables/useDatasetPreview'
import {
  normalizeSchemaColumns,
  normalizeSchemaTables,
  useSchemaHubState,
} from '../../composables/useSchemaHubState'
import { toast } from '../../composables/useToast'
import { useExecutionStore } from '../../stores/executionStore'
import { useUiStore } from '../../stores/uiStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import type { SchemaHubColumn, SchemaHubSelection, SchemaHubTable } from '../../types/schemaHub'
import { normalizeSchemaRefreshResult, schemaRefreshFeedback } from '../../utils/schemaRefresh'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import SchemaTableNavigator from '../schema/SchemaTableNavigator.vue'
import TableContextSurface from '../schema/TableContextSurface.vue'
import TableDataPreview from '../schema/TableDataPreview.vue'
import TableMetadataSurface from '../schema/TableMetadataSurface.vue'
import WorkspaceContextSurface from '../schema/WorkspaceContextSurface.vue'
import WorkspaceDataSources from '../schema/WorkspaceDataSources.vue'
import FloatingActionMenu from '../ui/FloatingActionMenu.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'

const executionStore = useExecutionStore()
const uiStore = useUiStore()
const workspaceStore = useWorkspaceStore()
const schemaHub = useSchemaHubState()

const savingTableId = ref('')
const savingTableContextId = ref('')
const isRefreshingSources = ref(false)
const removingDataset = ref(false)
const regeneratingTableName = ref('')
const pendingSelection = ref<SchemaHubSelection | null>(null)
const pendingDatasetRemoval = ref<SchemaHubTable | null>(null)
const activeWorkspaceSection = ref<'data' | 'context'>('data')
const lastSelectedTableId = ref('')
const sourceDrawerOpen = ref(false)
const dataSourcesRef = ref<InstanceType<typeof WorkspaceDataSources> | null>(null)
const sourceCount = ref(0)
const tableView = ref('preview')
const previewRevision = ref(0)
const datasetMenuOpen = ref(false)
const datasetMenuPosition = ref({ x: 0, y: 0 })
const schemaContext = ref('')
const groupedSchema = schemaHub.tables

const workspaceSections = [
  { value: 'data' as const, label: 'Data' },
  { value: 'context' as const, label: 'Context' },
]
const tableViewOptions = [
  { value: 'preview', label: 'Preview' },
  { value: 'schema', label: 'Schema' },
]
const schemaBusy = computed(() => (
  schemaHub.isLoading.value
  || isRefreshingSources.value
  || removingDataset.value
  || Boolean(savingTableId.value)
  || Boolean(savingTableContextId.value)
))
const hasWorkspace = computed(() => Boolean(workspaceStore.activeWorkspaceId))
const activeWorkspaceName = computed(() => {
  const activeId = String(workspaceStore.activeWorkspaceId || '')
  return String(workspaceStore.workspaces.find((workspace) => String(workspace.id) === activeId)?.name || 'Workspace')
})
const datasetMenuItems = computed(() => [
  {
    id: 'remove-dataset',
    label: 'Remove dataset',
    destructive: true,
    disabled: schemaBusy.value || schemaHub.isEdited.value,
  },
])

function openSourceDrawer() {
  if (!hasWorkspace.value || schemaBusy.value || schemaHub.isEdited.value) return
  datasetMenuOpen.value = false
  sourceDrawerOpen.value = true
}

function closeSourceDrawer() {
  sourceDrawerOpen.value = false
}

async function requestAddData() {
  if (!hasWorkspace.value || schemaBusy.value || schemaHub.isEdited.value) return
  openSourceDrawer()
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

function openWorkspaceSection(section: 'data' | 'context') {
  datasetMenuOpen.value = false
  if (section === activeWorkspaceSection.value) return
  if (section === 'context') {
    requestSchemaSelection({ kind: 'workspace' })
    return
  }
  const tableId = groupedSchema.value.some((table) => table.id === lastSelectedTableId.value)
    ? lastSelectedTableId.value
    : groupedSchema.value[0]?.id
  if (tableId) requestSchemaSelection({ kind: 'table', tableId })
  else activeWorkspaceSection.value = 'data'
}

function requestSchemaSelection(selection: SchemaHubSelection) {
  const currentSelection = schemaHub.selection.value
  const isCurrent = selection.kind === currentSelection.kind
    && (selection.kind === 'workspace' || (currentSelection.kind === 'table' && selection.tableId === currentSelection.tableId))
  if (isCurrent) {
    activeWorkspaceSection.value = selection.kind === 'workspace' ? 'context' : 'data'
    return
  }
  const currentTable = schemaHub.selectedTable.value
  if (currentTable && schemaHub.dirtyTableIds.value.has(currentTable.id)) {
    pendingSelection.value = selection
    return
  }
  applySchemaSelection(selection)
}

function applySchemaSelection(selection: SchemaHubSelection) {
  datasetMenuOpen.value = false
  if (selection.kind === 'workspace') {
    schemaHub.selectWorkspace()
    activeWorkspaceSection.value = 'context'
    return
  }
  schemaHub.selectTable(selection.tableId)
  lastSelectedTableId.value = selection.tableId
  activeWorkspaceSection.value = 'data'
}

function discardAndSelect() {
  const selection = pendingSelection.value
  const currentTable = schemaHub.selectedTable.value
  if (!selection) return
  if (currentTable) schemaHub.resetTable(currentTable.id)
  pendingSelection.value = null
  applySchemaSelection(selection)
}

function toggleDatasetActions(event: MouseEvent) {
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return
  const rect = target.getBoundingClientRect()
  datasetMenuPosition.value = { x: rect.right - 192, y: rect.bottom + 6 }
  datasetMenuOpen.value = !datasetMenuOpen.value
}

function handleDatasetAction(actionId: string) {
  datasetMenuOpen.value = false
  if (actionId === 'remove-dataset' && schemaHub.selectedTable.value) {
    pendingDatasetRemoval.value = schemaHub.selectedTable.value
  }
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && sourceDrawerOpen.value) closeSourceDrawer()
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
  } catch {
    if (workspaceStore.activeWorkspaceId !== workspaceId) return
    schemaContext.value = String(workspaceStore.workspaces.find((workspace: any) => workspace.id === workspaceId)?.schema_context || '').trim()
  }
}

async function fetchWorkspaceSchema() {
  if (!workspaceStore.activeWorkspaceId) return false
  const loadId = schemaHub.beginLoad()
  try {
    const workspaceId = workspaceStore.activeWorkspaceId
    const datasetResponse: any = await workspaceApi.listDatasets(workspaceId)
    const datasets = datasetResponse?.datasets || []
    const schemas = await Promise.all(datasets.map(async (dataset: any) => {
      try {
        return await workspaceApi.getDatasetSchema(workspaceId, dataset.table_name)
      } catch {
        return { table_name: dataset.table_name, context: '', columns: [] }
      }
    }))

    const applied = schemaHub.applyLoad(loadId, normalizeSchemaTables(datasets, schemas))
    if (applied && activeWorkspaceSection.value === 'data' && !schemaHub.selectedTable.value && groupedSchema.value[0]) {
      applySchemaSelection({ kind: 'table', tableId: groupedSchema.value[0].id })
    }
    return applied
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
    const workspace = workspaceStore.workspaces.find((candidate: any) => candidate.id === workspaceId)
    await workspaceApi.update(workspaceId, workspace?.name ?? null, context)
    if (workspaceStore.activeWorkspaceId !== workspaceId) {
      throw new DOMException('Workspace changed before the context save completed.', 'AbortError')
    }
    toast.success('Workspace context saved')
  } catch (error: any) {
    if (workspaceStore.activeWorkspaceId === workspaceId) toast.error('Failed to save context', error?.message)
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
    if (workspaceStore.activeWorkspaceId === workspaceId) toast.error('Failed to save table context', error?.message)
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
    if (workspaceStore.activeWorkspaceId === workspaceId) toast.error('Failed to save table schema', error?.message)
  } finally {
    savingTableId.value = ''
  }
}

async function regenerateTableSchema(tableName: string) {
  if (!workspaceStore.activeWorkspaceId || !tableName || regeneratingTableName.value) return
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
      context: schemaContext.value || '',
    })
    const table = groupedSchema.value.find((candidate) => candidate.tableName === tableName)
    if (table) {
      schemaHub.replaceTableColumns(table.id, normalizeSchemaColumns(table.id, tableName, regenerated.columns))
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

async function handleDatasetSchemaReady() {
  await fetchWorkspaceSchema()
}

onMounted(async () => {
  document.addEventListener('keydown', handleGlobalKeydown)
  await loadWorkspaceContext()
  await fetchWorkspaceSchema()
  window.addEventListener('dataset-schema-ready', handleDatasetSchemaReady)
  await nextTick()
  await handleRequestedAddData()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
  window.removeEventListener('dataset-schema-ready', handleDatasetSchemaReady)
})

watch(() => workspaceStore.activeWorkspaceId, async (newId) => {
  pendingSelection.value = null
  pendingDatasetRemoval.value = null
  sourceDrawerOpen.value = false
  datasetMenuOpen.value = false
  activeWorkspaceSection.value = 'data'
  lastSelectedTableId.value = ''
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
