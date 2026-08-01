<template>
  <div class="schema-editor h-full flex flex-col relative overflow-hidden bg-[var(--color-base)] text-[var(--color-text-main)] font-sans">
    <header class="schema-top-bar relative z-10 shrink-0 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 pt-4">
      <div class="flex flex-wrap items-center justify-between gap-4 pb-3">
        <div class="min-w-0">
          <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Workspace</p>
          <h2 class="mt-1 truncate text-[15px] font-semibold leading-tight tracking-tight">{{ activeWorkspaceName }}</h2>
        </div>
        <div class="flex items-center gap-2">
          <button v-if="activeWorkspaceSection === 'data'" type="button" @click="refreshWorkspaceSchema" :disabled="!hasWorkspace || schemaBusy || schemaHub.isEdited.value" :title="schemaHub.isEdited.value ? 'Save or discard table changes before refreshing' : 'Refresh data sources and reload schema'" class="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-50">
            <span v-if="isRefreshingSources" class="inquira-spinner h-3.5 w-3.5 border-2" aria-hidden="true"></span>
            <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M20 11a8.1 8.1 0 00-15.5-2M4 4v5h5m-5 4a8.1 8.1 0 0015.5 2M20 20v-5h-5"></path></svg>
            {{ isRefreshingSources ? 'Refreshing…' : 'Refresh' }}
          </button>
          <button
            type="button"
            class="btn-primary flex items-center gap-1.5 px-3 py-1.5 text-[13px]"
            :disabled="!hasWorkspace || schemaBusy || schemaHub.isEdited.value"
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

    <div v-else-if="activeWorkspaceSection === 'context'" class="min-h-0 flex-1 overflow-auto schema-scroll-area">
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

      <main class="min-w-0 flex-1 overflow-auto schema-scroll-area">
        <div v-if="schemaHub.isLoading.value" class="flex h-40 flex-col items-center justify-center">
          <div class="relative w-10 h-10 mb-3">
            <div class="absolute inset-0 rounded-full border-2 border-[var(--color-border)] opacity-30"></div>
            <div class="inquira-spinner absolute inset-0 border-2 border-r-transparent border-b-transparent border-l-transparent"></div>
          </div>
          <p class="text-sm font-medium text-[var(--color-text-muted)]">Loading workspace schema...</p>
        </div>
        <div v-if="!schemaHub.isLoading.value && groupedSchema.length === 0" class="flex h-40 flex-col items-center justify-center text-center">
          <p class="text-[var(--color-text-main)] font-medium text-[15px]">No datasets found.</p>
          <p class="mt-1 text-[13px] text-[var(--color-text-muted)]">Add a data source to begin exploring this workspace.</p>
          <button type="button" class="btn-primary mt-4 px-3 py-1.5 text-[13px]" @click="requestAddData">Add data</button>
        </div>
        <div v-else-if="!schemaHub.isLoading.value && schemaHub.selectedTable.value" class="space-y-4 p-4 pb-10">
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
import { useUiStore } from '../../stores/uiStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import TableMetadataSurface from '../schema/TableMetadataSurface.vue'
import TableContextSurface from '../schema/TableContextSurface.vue'
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
import { normalizeSchemaRefreshResult, schemaRefreshFeedback } from '../../utils/schemaRefresh'

const executionStore = useExecutionStore()
const uiStore = useUiStore()
const workspaceStore = useWorkspaceStore()

const schemaHub = useSchemaHubState()
const savingTableId = ref('')
const savingTableContextId = ref('')
const isRefreshingSources = ref(false)
const schemaBusy = computed(() => schemaHub.isLoading.value || isRefreshingSources.value || Boolean(savingTableId.value) || Boolean(savingTableContextId.value))
const regeneratingTableName = ref('')
const pendingSelection = ref<SchemaHubSelection | null>(null)
const groupedSchema = schemaHub.tables
const activeWorkspaceSection = ref<'data' | 'context'>('data')
const lastSelectedTableId = ref('')
const workspaceSections = [
  { value: 'data' as const, label: 'Data' },
  { value: 'context' as const, label: 'Context' },
]

const schemaContext = ref('')

const hasWorkspace = computed(() => !!workspaceStore.activeWorkspaceId)
const activeWorkspaceName = computed(() => {
  const activeId = String(workspaceStore.activeWorkspaceId || '')
  return String(workspaceStore.workspaces.find((workspace) => String(workspace.id) === activeId)?.name || 'Workspace')
})

function requestAddData() {
  if (!hasWorkspace.value || schemaBusy.value || schemaHub.isEdited.value) return
  uiStore.requestConnectionFlow()
}

function openWorkspaceSection(section: 'data' | 'context') {
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
  if (selection.kind === 'workspace') {
    schemaHub.selectWorkspace()
    activeWorkspaceSection.value = 'context'
  } else {
    schemaHub.selectTable(selection.tableId)
    lastSelectedTableId.value = selection.tableId
    activeWorkspaceSection.value = 'data'
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
})

onUnmounted(() => {
  window.removeEventListener('dataset-schema-ready', handleDatasetSchemaReady)
})

watch(() => workspaceStore.activeWorkspaceId, async (newId) => {
  pendingSelection.value = null
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
