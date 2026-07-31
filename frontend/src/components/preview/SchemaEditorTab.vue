<template>
  <div class="schema-editor h-full flex flex-col relative overflow-hidden bg-[var(--color-base)] text-[var(--color-text-main)] font-sans">
    <!-- Header -->
    <div class="schema-top-bar relative z-10 border-b border-[var(--color-border)] p-4 flex flex-wrap items-center justify-between gap-3 bg-[var(--color-surface)]">
      <div>
        <h2 class="text-[15px] font-bold leading-tight">Workspace Schema</h2>
        <p class="text-[13px] text-[var(--color-text-muted)] mt-1">Manage column metadata across all datasets</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="fetchWorkspaceSchema(true)" :disabled="schemaBusy || schemaHub.isEdited.value" :title="schemaHub.isEdited.value ? 'Save or discard table changes before refreshing' : undefined" class="px-3 py-1.5 rounded-md text-[13px] font-medium hover:bg-[var(--color-base-muted)] transition-colors disabled:opacity-50 text-[var(--color-text-main)]">Refresh</button>
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
          v-else
          v-show="schemaHub.selection.value.kind === 'workspace'"
          :key="workspaceStore.activeWorkspaceId"
          v-model="schemaContext"
          :save-context="saveWorkspaceContext"
        />
        <div v-if="!schemaHub.isLoading.value && groupedSchema.length === 0" class="flex h-40 flex-col items-center justify-center text-center">
          <p class="text-[var(--color-text-main)] font-medium text-[15px]">No datasets found.</p>
          <p class="text-[var(--color-text-muted)] text-[13px] mt-1">Upload data or sync a dataset first.</p>
        </div>
        <div v-else-if="!schemaHub.isLoading.value && schemaHub.selectedTable.value" class="p-4 pb-10">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { workspaceApi } from '../../api/workspaces'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import TableMetadataSurface from '../schema/TableMetadataSurface.vue'
import SchemaTableNavigator from '../schema/SchemaTableNavigator.vue'
import WorkspaceContextSurface from '../schema/WorkspaceContextSurface.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import {
  normalizeSchemaColumns,
  normalizeSchemaTables,
  useSchemaHubState,
} from '../../composables/useSchemaHubState'
import { toast } from '../../composables/useToast'
import type { SchemaHubColumn, SchemaHubSelection } from '../../types/schemaHub'

const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()

const schemaHub = useSchemaHubState()
const savingTableId = ref('')
const schemaBusy = computed(() => schemaHub.isLoading.value || Boolean(savingTableId.value))
const regeneratingTableName = ref('')
const pendingSelection = ref<SchemaHubSelection | null>(null)
const groupedSchema = schemaHub.tables

const schemaContext = ref('')

const hasWorkspace = computed(() => !!workspaceStore.activeWorkspaceId)

function requestSchemaSelection(selection: SchemaHubSelection) {
  const currentSelection = schemaHub.selection.value
  const isCurrent = selection.kind === currentSelection.kind
    && (selection.kind === 'workspace' || (currentSelection.kind === 'table' && selection.tableId === currentSelection.tableId))
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
  else schemaHub.selectTable(selection.tableId)
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

async function fetchWorkspaceSchema(forceRefresh = false) {
  if (!workspaceStore.activeWorkspaceId) return
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

    const applied = schemaHub.applyLoad(loadId, normalizeSchemaTables(datasets, schemas))
    if (applied && forceRefresh) toast.success('Schema refreshed', 'Loaded latest workspace schema.')
  } catch (error: any) {
    if (schemaHub.rejectLoad(loadId, error)) {
      toast.error('Failed to load schema', error?.message || 'Unknown error occurred.')
    }
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
