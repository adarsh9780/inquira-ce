<template>
  <section class="h-full">
    <div v-if="panelMode === 'ws-list'" class="space-y-4">
      <header class="space-y-1">
        <h2 class="text-lg font-bold text-[var(--color-text-main)]">Workspaces</h2>
        <p class="text-sm text-[var(--color-text-muted)]">Select a workspace to manage it, or create a new one.</p>
      </header>

      <button
        type="button"
        class="w-full rounded-lg border border-dashed border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-4 py-2.5 text-sm font-medium text-[var(--color-text-main)] transition-all hover:border-[var(--color-accent-border)] hover:text-[var(--color-accent)]"
        @click="emit('navigate', 'ws-create', 'forward')"
      >
        + New workspace
      </button>

      <div v-if="workspaceCards.length" class="space-y-2">
        <button
          v-for="workspace in workspaceCards"
          :key="workspace.id"
          type="button"
          class="w-full rounded-lg border px-3 py-3 text-left transition-all"
          :class="workspace.id === activeWorkspaceId
            ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)]'
            : 'border-[var(--color-border-strong)] bg-[var(--color-base)] hover:border-[var(--color-accent-border)]'"
          @click="openWorkspaceDetail(workspace.id)"
        >
          <div class="mb-2 flex items-start justify-between gap-2">
            <p
              class="truncate text-sm font-medium"
              :class="workspace.id === activeWorkspaceId ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'"
            >
              {{ workspace.name || 'Untitled workspace' }}
            </p>
            <span
              v-if="workspace.id === activeWorkspaceId"
              class="rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[11px] text-[var(--color-success)]"
            >
              Active
            </span>
          </div>
          <p class="text-xs text-[var(--color-text-muted)]">
            {{ workspace.filename }} · {{ workspace.conversationCount }} conversations · last active {{ workspace.lastActiveLabel }}
          </p>
        </button>
      </div>

      <div v-else class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-5 py-8 text-center">
        <svg viewBox="0 0 24 24" class="mx-auto mb-3 h-8 w-8 text-[var(--color-text-muted)]" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M3 7h6l2 2h10v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
        </svg>
        <p class="mb-4 text-sm text-[var(--color-text-sub)]">No workspaces yet</p>
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90"
          @click="emit('navigate', 'ws-create', 'forward')"
        >
          Create your first workspace
        </button>
      </div>
    </div>

    <div v-else-if="panelMode === 'ws-detail'" class="space-y-4">
      <header class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-[var(--color-text-main)]">{{ activeWorkspace?.name || 'Workspace detail' }}</h2>
          <p class="text-sm text-[var(--color-text-muted)]">{{ activeWorkspaceFilename }}</p>
        </div>
        <span
          class="rounded-full px-2 py-0.5 text-[11px]"
          :class="isWorkspaceActive ? 'bg-[var(--color-success-bg)] text-[var(--color-success)]' : 'bg-[var(--color-base-soft)] text-[var(--color-text-muted)]'"
        >
          {{ isWorkspaceActive ? 'Active' : 'Inactive' }}
        </span>
      </header>

      <div class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)]">
        <div class="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2 text-sm">
          <span class="text-[var(--color-text-muted)]">Created date</span>
          <span class="text-[var(--color-text-main)]">{{ detailCreatedAt }}</span>
        </div>
        <div class="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2 text-sm">
          <span class="text-[var(--color-text-muted)]">Conversations</span>
          <span class="text-[var(--color-text-main)]">{{ detailConversationCount }}</span>
        </div>
        <div class="flex items-center justify-between px-3 py-2 text-sm">
          <span class="text-[var(--color-text-muted)]">Last active</span>
          <span class="text-[var(--color-text-main)]">{{ detailLastActive }}</span>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Datasets</p>

        <div v-if="datasetEntries.length" class="space-y-2">
          <div
            v-for="dataset in datasetEntries"
            :key="dataset.table_name"
            class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)] px-3 py-2"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="mb-1 flex items-center gap-2">
                  <span class="rounded bg-[var(--color-base-soft)] px-1.5 py-0.5 text-[10px] uppercase text-[var(--color-text-muted)]">
                    {{ dataset.file_type || 'data' }}
                  </span>
                  <span class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ dataset.filename }}</span>
                </div>
                <p class="text-xs text-[var(--color-text-muted)]">
                  {{ datasetRowCount(dataset) }} rows · {{ datasetColumnCount(dataset) }} cols · {{ datasetFileSize(dataset) }}
                </p>
              </div>
              <div class="flex items-center gap-1">
                <button
                  type="button"
                  class="rounded p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-base-soft)] hover:text-[var(--color-accent)]"
                  title="Refresh dataset"
                  @click="refreshDataset(dataset)"
                >
                  <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                    <path d="M20 4v6h-6" />
                  </svg>
                </button>
                <button
                  type="button"
                  class="rounded p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-base-soft)] hover:text-[var(--color-danger)]"
                  title="Remove dataset"
                  @click="requestRemoveDataset(dataset.table_name)"
                >
                  <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M5 7h14" />
                    <path d="M9 7V5h6v2" />
                    <path d="M8 7l1 12h6l1-12" />
                  </svg>
                </button>
              </div>
            </div>

            <div
              v-if="pendingRemovalTable === dataset.table_name"
              class="mt-2 flex items-center justify-end gap-2 border-t border-[var(--color-border)] pt-2"
            >
              <span class="mr-auto text-xs text-[var(--color-text-muted)]">Remove this dataset?</span>
              <button
                type="button"
                class="rounded border border-[var(--color-border-strong)] px-2 py-1 text-xs text-[var(--color-text-sub)]"
                @click="pendingRemovalTable = ''"
              >
                Cancel
              </button>
              <button
                type="button"
                class="rounded bg-[var(--color-danger)] px-2 py-1 text-xs font-medium text-white"
                @click="confirmRemoveDataset(dataset)"
              >
                Remove
              </button>
            </div>
          </div>
        </div>

        <p v-else class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-3 text-sm text-[var(--color-text-muted)]">
          No datasets loaded for this workspace.
        </p>

        <button
          type="button"
          class="w-full rounded-lg border border-dashed border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] transition-all hover:border-[var(--color-accent-border)] hover:text-[var(--color-accent)]"
          @click="openDatasetPicker"
        >
          + Add dataset
        </button>
      </div>

      <div v-if="showRenameEditor" class="space-y-2 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-3">
        <label class="block text-xs text-[var(--color-text-sub)]">Rename workspace</label>
        <input
          v-model="renameValue"
          type="text"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
        />
        <div class="flex justify-end gap-2">
          <button type="button" class="rounded border border-[var(--color-border-strong)] px-3 py-1.5 text-xs" @click="cancelRename">Cancel</button>
          <button type="button" class="rounded bg-[var(--color-accent)] px-3 py-1.5 text-xs font-medium text-white" @click="saveRename">Save</button>
        </div>
      </div>

      <div v-if="showDeleteConfirm" class="space-y-2 rounded-lg border border-[var(--color-danger)]/25 bg-[var(--color-base-soft)] px-3 py-3">
        <p class="text-sm text-[var(--color-danger)]">Delete this workspace and all its datasets?</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="rounded border border-[var(--color-border-strong)] px-3 py-1.5 text-xs" @click="showDeleteConfirm = false">Cancel</button>
          <button type="button" class="rounded bg-[var(--color-danger)] px-3 py-1.5 text-xs font-medium text-white" @click="deleteWorkspace">Delete</button>
        </div>
      </div>

      <footer class="flex items-center justify-between border-t border-[var(--color-border)] pt-3">
        <button type="button" class="text-sm text-[var(--color-danger)]" @click="showDeleteConfirm = !showDeleteConfirm">Delete workspace…</button>
        <button type="button" class="text-sm text-[var(--color-accent)]" @click="startRename">Rename</button>
      </footer>
    </div>

    <div v-else class="space-y-4">
      <header class="space-y-1">
        <h2 class="text-lg font-bold text-[var(--color-text-main)]">New workspace</h2>
        <p class="text-sm text-[var(--color-text-muted)]">Create a workspace and optionally attach a dataset.</p>
      </header>

      <label class="space-y-1">
        <span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Workspace name</span>
        <input
          v-model="newWorkspaceName"
          type="text"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          placeholder="e.g. Sales analysis"
        />
      </label>

      <div class="space-y-2">
        <span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Dataset</span>
        <button
          type="button"
          class="w-full rounded-lg border border-dashed border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-4 py-8 text-center text-sm text-[var(--color-text-sub)] transition-all hover:border-[var(--color-accent-border)] hover:text-[var(--color-accent)]"
          @click="pickNewWorkspaceDataset"
        >
          <span v-if="newWorkspaceDatasetPath">{{ newWorkspaceDatasetPath }}</span>
          <span v-else>Drop a dataset here or click to browse</span>
        </button>
      </div>

      <label class="space-y-1">
        <span class="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
          Context
          <span class="rounded bg-[var(--color-base-soft)] px-1.5 py-0.5 text-[10px] normal-case tracking-normal text-[var(--color-text-muted)]">Optional</span>
        </span>
        <textarea
          v-model="newWorkspaceContext"
          rows="4"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          placeholder="Add context to guide schema generation..."
        ></textarea>
      </label>

      <div class="flex justify-end border-t border-[var(--color-border)] pt-3">
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isCreatingWorkspace"
          @click="createWorkspace"
        >
          <span v-if="isCreatingWorkspace" class="inline-flex items-center gap-2">
            <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
            Creating...
          </span>
          <span v-else>Create workspace</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { apiService } from '../../../services/apiService'
import { useAppStore } from '../../../stores/appStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'

const props = defineProps({
  panelMode: {
    type: String,
    default: 'ws-list',
  },
  activeWorkspaceId: {
    type: String,
    default: '',
  },
  workspaces: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['navigate', 'set-active-workspace'])

const appStore = useAppStore()

const workspaceSummaries = ref({})
const workspaceDetail = ref(null)
const datasetEntries = ref([])
const datasetColumnCounts = ref({})
const datasetFileSizes = ref({})
const pendingRemovalTable = ref('')
const showRenameEditor = ref(false)
const renameValue = ref('')
const showDeleteConfirm = ref(false)

const newWorkspaceName = ref('')
const newWorkspaceDatasetPath = ref('')
const newWorkspaceContext = ref('')
const isCreatingWorkspace = ref(false)

const workspaceCards = computed(() => {
  const items = Array.isArray(props.workspaces) ? props.workspaces : []
  return items.map((workspace) => {
    const id = String(workspace?.id || '').trim()
    const name = String(workspace?.name || '').trim()
    const duckdbPath = String(workspace?.duckdb_path || '').trim()
    const filename = duckdbPath.split('/').pop() || 'workspace.duckdb'
    const summary = workspaceSummaries.value?.[id] || {}
    const conversationCount = Number(summary?.conversation_count || 0)
    const lastActive = String(workspace?.updated_at || '').trim()
    return {
      ...workspace,
      id,
      name,
      filename,
      conversationCount,
      lastActiveLabel: formatRelativeTime(lastActive),
    }
  })
})

const activeWorkspace = computed(() => workspaceCards.value.find((workspace) => workspace.id === String(props.activeWorkspaceId || '').trim()) || null)
const activeWorkspaceFilename = computed(() => activeWorkspace.value?.filename || 'workspace.duckdb')
const isWorkspaceActive = computed(() => !!activeWorkspace.value && !!activeWorkspace.value.is_active)
const detailCreatedAt = computed(() => formatDateTime(workspaceDetail.value?.created_at || activeWorkspace.value?.created_at))
const detailConversationCount = computed(() => Number(workspaceDetail.value?.conversation_count || 0))
const detailLastActive = computed(() => formatRelativeTime(workspaceDetail.value?.updated_at || activeWorkspace.value?.updated_at))

watch(
  () => props.panelMode,
  async (nextMode) => {
    if (nextMode === 'ws-list') {
      await hydrateWorkspaceCards()
    }
    if (nextMode === 'ws-detail') {
      await loadWorkspaceDetail()
      await loadWorkspaceDatasets()
    }
  },
  { immediate: true },
)

watch(
  () => props.workspaces,
  async () => {
    if (props.panelMode === 'ws-list') {
      await hydrateWorkspaceCards()
    }
  },
  { deep: true },
)

watch(
  () => props.activeWorkspaceId,
  async () => {
    if (props.panelMode !== 'ws-detail') return
    await loadWorkspaceDetail()
    await loadWorkspaceDatasets()
  },
)

onMounted(async () => {
  if (props.panelMode === 'ws-list') {
    await hydrateWorkspaceCards()
  }
})

async function hydrateWorkspaceCards() {
  const ids = workspaceCards.value.map((workspace) => workspace.id).filter(Boolean)
  if (!ids.length) {
    workspaceSummaries.value = {}
    return
  }
  const summaries = {}
  await Promise.all(
    ids.map(async (workspaceId) => {
      try {
        const summary = await apiService.v1GetWorkspaceSummary(workspaceId)
        summaries[workspaceId] = summary
      } catch {
        summaries[workspaceId] = {}
      }
    }),
  )
  workspaceSummaries.value = summaries
}

async function openWorkspaceDetail(workspaceId) {
  await emitActiveWorkspace(workspaceId)
  emit('navigate', 'ws-detail', 'forward')
}

async function emitActiveWorkspace(workspaceId) {
  const id = String(workspaceId || '').trim()
  if (!id) return
  emit('set-active-workspace', id)
}

async function loadWorkspaceDetail() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    workspaceDetail.value = null
    return
  }
  try {
    workspaceDetail.value = await apiService.v1GetWorkspaceSummary(workspaceId)
  } catch {
    workspaceDetail.value = null
  }
}

async function loadWorkspaceDatasets() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    datasetEntries.value = []
    return
  }
  try {
    const response = await apiService.v1ListDatasets(workspaceId)
    const datasets = Array.isArray(response?.datasets) ? response.datasets : []
    datasetEntries.value = datasets.map((item) => ({
      table_name: String(item?.table_name || '').trim(),
      source_path: String(item?.source_path || '').trim(),
      row_count: Number.isFinite(Number(item?.row_count)) ? Number(item.row_count) : null,
      file_type: String(item?.file_type || '').trim().toLowerCase(),
      filename: formatFilename(item?.source_path || item?.table_name || ''),
    })).filter((item) => item.table_name)
    await enrichDatasetMetadata(workspaceId)
  } catch (error) {
    datasetEntries.value = []
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to load datasets.'))
  }
}

async function enrichDatasetMetadata(workspaceId) {
  const columnCounts = {}
  const fileSizes = {}

  await Promise.all(
    datasetEntries.value.map(async (dataset) => {
      try {
        const schema = await apiService.v1GetDatasetSchema(workspaceId, dataset.table_name)
        const columns = Array.isArray(schema?.columns) ? schema.columns : []
        columnCounts[dataset.table_name] = columns.length
      } catch {
        columnCounts[dataset.table_name] = null
      }

      try {
        fileSizes[dataset.table_name] = await resolveDatasetFileSize(dataset.source_path)
      } catch {
        fileSizes[dataset.table_name] = null
      }
    }),
  )

  datasetColumnCounts.value = columnCounts
  datasetFileSizes.value = fileSizes
}

async function resolveDatasetFileSize(path) {
  const normalized = String(path || '').trim()
  if (!normalized || normalized.startsWith('browser://')) return null
  if (typeof window === 'undefined' || !window.__TAURI_INTERNALS__) return null
  const { stat } = await import('@tauri-apps/plugin-fs')
  const info = await stat(normalized)
  const bytes = Number(info?.size || 0)
  return Number.isFinite(bytes) && bytes > 0 ? bytes : null
}

function datasetRowCount(dataset) {
  const value = Number(dataset?.row_count || 0)
  return Number.isFinite(value) && value > 0 ? value.toLocaleString() : '?'
}

function datasetColumnCount(dataset) {
  const value = Number(datasetColumnCounts.value?.[dataset?.table_name] || 0)
  return Number.isFinite(value) && value > 0 ? value : '?'
}

function datasetFileSize(dataset) {
  const bytes = Number(datasetFileSizes.value?.[dataset?.table_name] || 0)
  if (!Number.isFinite(bytes) || bytes <= 0) return 'unknown size'
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}

function requestRemoveDataset(tableName) {
  pendingRemovalTable.value = String(tableName || '').trim()
}

async function confirmRemoveDataset(dataset) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const tableName = String(dataset?.table_name || '').trim()
  if (!workspaceId || !tableName) return
  try {
    await apiService.v1DeleteDataset(workspaceId, tableName)
    pendingRemovalTable.value = ''
    await loadWorkspaceDatasets()
    toast.success('Dataset removed', 'Dataset removed from workspace.')
  } catch (error) {
    toast.error('Remove failed', extractApiErrorMessage(error, 'Failed to remove dataset.'))
  }
}

async function refreshDataset(dataset) {
  const sourcePath = String(dataset?.source_path || '').trim()
  if (!sourcePath || sourcePath.startsWith('browser://')) {
    toast.error('Refresh failed', 'This dataset cannot be refreshed from source.')
    return
  }
  try {
    await apiService.uploadDataPath(sourcePath)
    await loadWorkspaceDatasets()
    toast.success('Dataset refreshed', 'Dataset refreshed successfully.')
  } catch (error) {
    toast.error('Refresh failed', extractApiErrorMessage(error, 'Failed to refresh dataset.'))
  }
}

async function openDatasetPicker() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Data files', extensions: ['csv', 'parquet', 'xlsx', 'xls', 'json', 'tsv'] }],
    })
    const selectedPath = Array.isArray(selected) ? String(selected[0] || '').trim() : String(selected || '').trim()
    if (!selectedPath) return
    await apiService.uploadDataPath(selectedPath)
    await loadWorkspaceDatasets()
    toast.success('Dataset added', 'Dataset added to workspace.')
  } catch (error) {
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to add dataset.'))
  }
}

function startRename() {
  renameValue.value = String(activeWorkspace.value?.name || '').trim()
  showRenameEditor.value = true
}

function cancelRename() {
  showRenameEditor.value = false
  renameValue.value = ''
}

async function saveRename() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(renameValue.value || '').trim()
  if (!workspaceId || !name) return
  try {
    await appStore.renameWorkspace(workspaceId, name)
    await appStore.fetchWorkspaces()
    showRenameEditor.value = false
    toast.success('Workspace renamed', 'Workspace name updated.')
  } catch (error) {
    toast.error('Rename failed', extractApiErrorMessage(error, 'Failed to rename workspace.'))
  }
}

async function deleteWorkspace() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  try {
    await appStore.deleteWorkspaceAsync(workspaceId)
    showDeleteConfirm.value = false
    await appStore.fetchWorkspaces()
    const fallbackId = String(appStore.activeWorkspaceId || workspaceCards.value[0]?.id || '').trim()
    if (fallbackId) {
      emit('set-active-workspace', fallbackId)
    }
    emit('navigate', 'ws-list', 'backward')
    toast.success('Workspace deletion started', 'Workspace deletion is running in background.')
  } catch (error) {
    toast.error('Delete failed', extractApiErrorMessage(error, 'Failed to delete workspace.'))
  }
}

async function pickNewWorkspaceDataset() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Data files', extensions: ['csv', 'parquet', 'xlsx', 'xls', 'json', 'tsv'] }],
    })
    const selectedPath = Array.isArray(selected) ? String(selected[0] || '').trim() : String(selected || '').trim()
    if (!selectedPath) return
    newWorkspaceDatasetPath.value = selectedPath
  } catch (error) {
    toast.error('File picker failed', extractApiErrorMessage(error, 'Failed to select dataset file.'))
  }
}

async function createWorkspace() {
  const name = String(newWorkspaceName.value || '').trim()
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  isCreatingWorkspace.value = true
  try {
    const workspace = await appStore.createWorkspace(name)
    const workspaceId = String(workspace?.id || appStore.activeWorkspaceId || '').trim()
    if (workspaceId) {
      emit('set-active-workspace', workspaceId)
    }
    if (newWorkspaceDatasetPath.value) {
      await apiService.uploadDataPath(newWorkspaceDatasetPath.value)
    }
    if (String(newWorkspaceContext.value || '').trim()) {
      await apiService.v1UpdatePreferences({
        schema_context: String(newWorkspaceContext.value || '').trim(),
      })
    }
    await appStore.fetchWorkspaces()
    emit('navigate', 'ws-detail', 'forward')
    newWorkspaceName.value = ''
    newWorkspaceDatasetPath.value = ''
    newWorkspaceContext.value = ''
    toast.success('Workspace created', 'Workspace created')
  } catch (error) {
    toast.error('Create failed', extractApiErrorMessage(error, 'Failed to create workspace.'))
  } finally {
    isCreatingWorkspace.value = false
  }
}

function formatFilename(raw) {
  const value = String(raw || '').trim()
  if (!value) return 'dataset'
  const last = value.split('/').pop() || value
  return last
}

function formatDateTime(raw) {
  const value = String(raw || '').trim()
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString()
}

function formatRelativeTime(raw) {
  const value = String(raw || '').trim()
  if (!value) return 'unknown'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'unknown'
  const deltaMs = Date.now() - parsed.getTime()
  const minutes = Math.max(1, Math.round(deltaMs / 60000))
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}
</script>
