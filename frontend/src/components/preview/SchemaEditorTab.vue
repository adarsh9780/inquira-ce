<template>
  <div class="schema-editor h-full flex flex-col relative overflow-hidden bg-[var(--color-base)] text-[var(--color-text-main)] font-sans">
    <!-- Header -->
    <div class="schema-top-bar relative z-10 border-b border-[var(--color-border)] p-4 flex flex-wrap items-center justify-between gap-3 bg-[var(--color-surface)]">
      <div>
        <h2 class="text-[15px] font-bold leading-tight">Workspace Schema</h2>
        <p class="text-[13px] text-[var(--color-text-muted)] mt-1">Manage column metadata across all datasets</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="fetchWorkspaceSchema(true)" :disabled="schemaLoading" class="px-3 py-1.5 rounded-md text-[13px] font-medium hover:bg-[var(--color-base-muted)] transition-colors disabled:opacity-50 text-[var(--color-text-main)]">Refresh</button>
        <button @click="saveAllSchema" :disabled="!schemaEdited || schemaLoading" class="px-3 py-1.5 rounded-md text-[13px] font-medium bg-[var(--color-accent)] text-[var(--color-on-accent)] disabled:opacity-50 hover:brightness-95 transition-all shadow-sm">Save Changes</button>
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
    <div v-else class="flex flex-col flex-1 overflow-hidden">
      <WorkspaceContextSurface
        :key="workspaceStore.activeWorkspaceId"
        v-model="schemaContext"
        :save-context="saveWorkspaceContext"
      />

      <!-- Schema Tables -->
      <div class="flex-1 overflow-auto p-4 schema-scroll-area">
        <div v-if="schemaLoading" class="flex h-40 flex-col items-center justify-center">
          <div class="relative w-10 h-10 mb-3">
            <div class="absolute inset-0 rounded-full border-2 border-[var(--color-border)] opacity-30"></div>
            <div class="inquira-spinner absolute inset-0 border-2 border-r-transparent border-b-transparent border-l-transparent"></div>
          </div>
          <p class="text-sm font-medium text-[var(--color-text-muted)]">Loading workspace schema...</p>
        </div>
        <div v-else-if="groupedSchema.length === 0" class="flex h-40 flex-col items-center justify-center text-center">
          <p class="text-[var(--color-text-main)] font-medium text-[15px]">No datasets found.</p>
          <p class="text-[var(--color-text-muted)] text-[13px] mt-1">Upload data or sync a dataset first.</p>
        </div>
        <div v-else class="space-y-8 pb-10">
          <div v-for="group in groupedSchema" :key="group.tableName" class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-sm overflow-hidden flex flex-col">
            <!-- Table Sub-header Sticky -->
            <div class="sticky top-0 z-30 bg-[var(--color-surface)]/95 backdrop-blur-sm px-4 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
              <h3 class="font-mono text-[14px] font-semibold text-[var(--color-text-main)] flex items-center gap-2">
                <svg class="w-4 h-4 text-[var(--color-accent)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
                {{ group.tableName }}
              </h3>
              <div class="flex items-center gap-2.5">
                <button @click="regenerateTableSchema(group.tableName)" :disabled="schemaLoading || Boolean(regeneratingTableName)" class="text-[12px] font-medium text-[var(--color-accent)] hover:bg-[var(--color-accent)]/10 px-2 py-0.5 rounded transition-colors flex items-center gap-1 disabled:cursor-not-allowed disabled:opacity-60" title="Regenerate descriptions for this table only">
                  <span v-if="regeneratingTableName === group.tableName" class="inquira-spinner h-3.5 w-3.5 border-2"></span>
                  <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                  </svg>
                  {{ regeneratingTableName === group.tableName ? 'Regenerating...' : 'Regenerate' }}
                </button>
                <span class="text-[12px] font-medium text-[var(--color-text-muted)] bg-[var(--color-base)] px-2 py-1 rounded-md border border-[var(--color-border)]">{{ group.columns.length }} columns</span>
              </div>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse min-w-[600px]">
                <thead class="sticky top-[45px] z-20 bg-[var(--color-surface)] border-b border-[var(--color-border)]">
                  <tr>
                    <th class="px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] w-12 text-center border-b border-[var(--color-border)]">#</th>
                    <th class="px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] w-1/4 border-b border-[var(--color-border)]">Column</th>
                    <th class="px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] w-1/3 border-b border-[var(--color-border)]">Description</th>
                    <th class="px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)] w-1/3 border-b border-[var(--color-border)]">Aliases</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--color-border)]">
                  <tr v-for="(col, i) in group.columns" :key="col.name" class="hover:bg-[var(--color-base-muted)] transition-colors group/row align-top">
                    <td class="px-4 py-3.5 text-[12px] text-[var(--color-text-sub)] text-center w-12">{{ i + 1 }}</td>
                    <td class="px-4 py-3.5 text-[13px] font-mono font-semibold text-[var(--color-text-main)] w-1/4">{{ col.name }}</td>
                    <td class="px-4 py-2 w-1/3 cursor-pointer group/cell relative" @click="startInlineEdit(col, 'description')">
                      <div v-if="editingCell?.col === col && editingCell?.field === 'description'" class="relative pt-1.5" @click.stop>
                        <textarea v-focus v-model="editingCell.value" @blur="saveInlineEdit" @keydown.esc.prevent="cancelInlineEdit" @keydown.enter.ctrl.prevent="saveInlineEdit" class="w-full bg-[var(--color-base)] border border-[var(--color-accent)] rounded-md p-2 text-[13px] text-[var(--color-text-main)] resize-y min-h-[60px] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 shadow-sm" placeholder="Enter description..."></textarea>
                        <div class="absolute right-2 bottom-3 text-[10px] text-[var(--color-text-muted)] pointer-events-none">Ctrl+Enter to save</div>
                      </div>
                      <div v-else class="min-h-[28px] py-1.5 text-[13px] text-[var(--color-text-main)] whitespace-pre-wrap pr-8">
                        <span v-if="col.description">{{ col.description }}</span>
                        <span v-else class="text-[var(--color-text-muted)] italic text-[12px]">Click to add description...</span>
                        <div class="absolute right-3 top-2.5 opacity-0 group-hover/cell:opacity-100 text-[var(--color-text-muted)] bg-[var(--color-base)] rounded p-1 shadow-sm border border-[var(--color-border)] transition-opacity">
                           <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-2 w-1/3 cursor-pointer group/cell relative" @click="startInlineEdit(col, 'aliases')">
                      <div v-if="editingCell?.col === col && editingCell?.field === 'aliases'" class="relative pt-1.5" @click.stop>
                        <input v-focus v-model="editingCell.value" @blur="saveInlineEdit" @keydown.esc.prevent="cancelInlineEdit" @keydown.enter.prevent="saveInlineEdit" class="w-full bg-[var(--color-base)] border border-[var(--color-accent)] rounded-md p-2 text-[13px] text-[var(--color-text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20 shadow-sm" placeholder="alias1, alias2" />
                        <div class="absolute right-2 top-3 text-[10px] text-[var(--color-text-muted)] pointer-events-none">Enter to save</div>
                      </div>
                      <div v-else class="min-h-[28px] py-1.5 text-[13px]">
                        <div v-if="col.aliases && col.aliases.length > 0" class="flex flex-wrap gap-1.5 pr-8">
                          <span v-for="(alias, ai) in col.aliases" :key="ai" class="inline-flex items-center px-2 py-0.5 rounded border border-[var(--color-border)] bg-[var(--color-base-muted)] text-[var(--color-text-main)] text-[11px] font-mono shadow-sm">
                            {{ alias }}
                          </span>
                        </div>
                        <span v-else class="text-[var(--color-text-muted)] italic text-[12px]">Click to add aliases...</span>
                        <div class="absolute right-3 top-2.5 opacity-0 group-hover/cell:opacity-100 text-[var(--color-text-muted)] bg-[var(--color-base)] rounded p-1 shadow-sm border border-[var(--color-border)] transition-opacity">
                           <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                        </div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { workspaceApi } from '../../api/workspaces'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import WorkspaceContextSurface from '../schema/WorkspaceContextSurface.vue'
import {
  normalizeAliasList,
  normalizeSchemaColumns,
  normalizeSchemaTables,
  useSchemaHubState,
} from '../../composables/useSchemaHubState'
import { toast } from '../../composables/useToast'
import type { SchemaHubColumn } from '../../types/schemaHub'

// Custom Directive for autofocusing inline edit inputs
const vFocus = {
  mounted: (el: any) => el.focus()
}

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()

const schemaHub = useSchemaHubState()
const schemaSaving = ref(false)
const schemaLoading = computed(() => schemaHub.isLoading.value || schemaSaving.value)
const regeneratingTableName = ref('')
const schemaEdited = schemaHub.isEdited
const groupedSchema = schemaHub.tables

const schemaContext = ref('')

// Inline editing state
const editingCell = ref<{
  col: SchemaHubColumn
  field: 'description' | 'aliases'
  value: string
} | null>(null)

const hasWorkspace = computed(() => !!workspaceStore.activeWorkspaceId)

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

function startInlineEdit(col: SchemaHubColumn, field: 'description' | 'aliases') {
  if (editingCell.value && editingCell.value.col === col && editingCell.value.field === field) return

  // Save previous edit if exists
  if (editingCell.value) {
    saveInlineEdit()
  }

  editingCell.value = {
    col,
    field,
    value: field === 'description' ? (col.description || '') : (col.aliases || []).join(', ')
  }
}

function cancelInlineEdit() {
  editingCell.value = null
}

function saveInlineEdit() {
  if (!editingCell.value) return
  const { col, field, value } = editingCell.value

  let changed = false
  if (field === 'description') {
    if (col.description !== value) {
      col.description = value
      changed = true
    }
  } else if (field === 'aliases') {
    const newAliases = normalizeAliasList(value)
    // Simple array equality check
    if (JSON.stringify(col.aliases) !== JSON.stringify(newAliases)) {
      col.aliases = newAliases
      changed = true
    }
  }

  if (changed) {
    schemaHub.markTableDirty(col.tableId)
  }

  editingCell.value = null
}

async function saveAllSchema() {
  if (!schemaEdited.value || !workspaceStore.activeWorkspaceId) return

  // If user clicks save while editing, commit the inline edit first
  if (editingCell.value) {
    saveInlineEdit()
  }

  schemaSaving.value = true
  try {
    const workspaceId = workspaceStore.activeWorkspaceId

    // Only save the tables that have been modified
    const tablesToSave = groupedSchema.value.filter(g => schemaHub.dirtyTableIds.value.has(g.id))

    for (const group of tablesToSave) {
      await workspaceApi.saveDatasetSchema(workspaceId, group.tableName, {
        context: schemaContext.value || '',
        columns: group.columns.map((c: any) => ({
          name: c.name,
          dtype: c.dataType || 'VARCHAR',
          description: c.description || '',
          aliases: c.aliases || []
        }))
      })
    }

    schemaHub.clearDirtyTables()
    toast.success('Schema saved', `Saved changes for ${tablesToSave.length} table(s).`)
  } catch (error: any) {
    toast.error('Failed to save schema', error?.message)
  } finally {
    schemaSaving.value = false
  }
}


async function regenerateTableSchema(tableName: any) {
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
  schemaHub.clear()
  if (newId) {
    await loadWorkspaceContext()
    await fetchWorkspaceSchema()
  } else {
    schemaContext.value = ''
  }
})

watch(() => uiStore.activeTab, async (nextTab) => {
  if (nextTab !== 'schema-editor') {
    // If navigating away and there are unsaved changes, we could potentially auto-save or prompt.
    // For now, let's keep it simple.
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
