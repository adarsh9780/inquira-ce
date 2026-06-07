<template>
  <section class="scrollbar-hidden h-full overflow-y-auto">
    <div class="grid h-full min-h-0 grid-cols-[240px_1fr] gap-6">
      <aside class="flex h-full min-h-0 flex-col border-r border-[var(--color-border)] pr-4 select-none">
        <header class="mb-3 flex items-center justify-between">
          <h3 class="section-label">Workspaces</h3>
          <button type="button" class="text-xs font-semibold text-[var(--color-accent)] hover:underline" @click="beginInlineCreate">
            + New
          </button>
        </header>

        <div class="flex-1 space-y-2 overflow-y-auto pr-1 scrollbar-thin">
          <div
            v-if="isInlineCreating"
            class="rounded-lg bg-[var(--color-accent-soft)] px-3 py-2.5 ring-1 ring-[var(--color-accent-border)]"
          >
            <input
              ref="newWorkspaceInputRef"
              v-model="setupWorkspaceName"
              type="text"
              class="w-full bg-transparent text-xs font-medium text-[var(--color-text-main)] outline-none placeholder:text-[var(--color-text-muted)]"
              placeholder="New workspace name"
              :disabled="isCreatingWorkspace"
              @keydown.enter.prevent="createWorkspace"
              @keydown.escape.prevent="cancelInlineCreate"
            />
            <p class="mt-1 text-[10px] text-[var(--color-text-muted)]">Press Enter to create</p>
          </div>

          <div
            v-for="workspace in workspaceCards"
            :key="workspace.id"
            class="group relative flex w-full cursor-pointer flex-col rounded-lg px-3 py-2.5 text-left transition-all"
            :class="workspace.id === activeWorkspaceId
              ? 'bg-[var(--color-accent-soft)] ring-1 ring-[var(--color-accent-border)]'
              : 'bg-[var(--color-base-soft)] hover:bg-[var(--color-base-muted)]'"
            @click="selectWorkspaceSummary(workspace.id)"
          >
            <div class="flex items-start justify-between gap-2">
              <p class="min-w-0 flex-1 truncate text-xs font-medium text-[var(--color-text-main)]">{{ workspace.name || 'Untitled workspace' }}</p>
              <div class="flex shrink-0 items-center gap-1.5">
                <span v-if="workspace.id === activeWorkspaceId" class="rounded-full bg-[var(--color-accent-soft)] px-1.5 py-0.5 text-[9px] text-[var(--color-accent)]">Selected</span>
                <span v-if="workspace.is_active" class="rounded-full bg-[var(--color-success-bg)] px-1.5 py-0.5 text-[9px] text-[var(--color-success)]">Active</span>
                <button
                  type="button"
                  class="rounded p-1 text-[var(--color-text-muted)] opacity-40 transition-all hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] focus-visible:opacity-100 group-hover:opacity-100"
                  title="Delete workspace"
                  aria-label="Delete workspace"
                  @click.stop="requestDeleteWorkspace(workspace.id)"
                >
                  <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M5 7h14" /><path d="M9 7V5h6v2" /><path d="M8 7l1 12h6l1-12" />
                  </svg>
                </button>
              </div>
            </div>
            <p class="mt-1 text-[10px] text-[var(--color-text-muted)]">{{ workspace.conversationCount }} convs · {{ workspace.lastActiveLabel }}</p>
          </div>

          <p v-if="!workspaceCards.length && !isInlineCreating" class="py-4 text-center text-xs text-[var(--color-text-muted)]">No workspaces yet</p>
        </div>
      </aside>

      <div class="flex h-full min-w-0 flex-col">
        <div v-if="workspaceSurface === 'summary'" class="flex h-full flex-1 flex-col space-y-4">
          <header class="border-b border-[var(--color-border)] pb-2">
            <h2 class="text-sm font-bold text-[var(--color-text-main)]">Selected Workspace Summary</h2>
          </header>

          <div v-if="activeWorkspace" class="flex-1 space-y-4 overflow-y-auto scrollbar-thin">
            <div class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] p-3">
              <div class="mb-3 flex min-w-0 items-start justify-between gap-3 border-b border-[var(--color-border)] pb-3">
                <div class="min-w-0">
                  <span class="section-label mb-1 block">Selected workspace</span>
                  <input
                    v-if="isRenamingInline"
                    ref="renameInputRef"
                    v-model="renameValue"
                    class="input-base input-outlined w-full py-1 text-sm"
                    @keydown.enter.prevent="saveRename"
                    @keydown.escape.prevent="cancelRename"
                  />
                  <p v-else class="truncate text-sm font-semibold text-[var(--color-text-main)]">{{ activeWorkspace.name }}</p>
                </div>
                <div class="flex shrink-0 flex-wrap items-center justify-end gap-2">
                  <template v-if="isRenamingInline">
                    <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="cancelRename">Cancel</button>
                    <button type="button" class="btn-primary px-3 py-1.5 text-xs" @click="saveRename">Save</button>
                  </template>
                  <template v-else>
                    <button v-if="!isWorkspaceActive" type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="activateSelectedWorkspace">Activate</button>
                    <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="startRename">Rename</button>
                    <button type="button" class="btn-primary px-3 py-1.5 text-xs" @click="openWorkspaceEditor">Edit</button>
                  </template>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                <div class="min-w-0">
                  <span class="section-label mb-1 block">Conversations</span>
                  <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ activeWorkspace.conversationCount }}</p>
                </div>
                <div class="min-w-0">
                  <span class="section-label mb-1 block">Last Active</span>
                  <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ activeWorkspace.lastActiveLabel }}</p>
                </div>
              </div>
            </div>

            <div class="space-y-2">
              <h4 class="section-label mb-2">Linked Datasets</h4>
              <div v-if="datasetEntries.length" class="space-y-2">
                <div v-for="dataset in datasetEntries" :key="dataset.table_name" class="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-2.5">
                  <div class="min-w-0"><p class="truncate text-xs font-medium text-[var(--color-text-main)]">{{ dataset.filename }}</p><p class="mt-0.5 text-[10px] text-[var(--color-text-muted)]">{{ datasetMetadata(dataset) }}</p></div>
                  <span class="rounded-full px-2 py-0.5 text-[9px] font-medium" :class="datasetSchemaStatusBadgeClass(dataset)">{{ datasetSchemaStatusLabel(dataset) }}</span>
                </div>
              </div>
              <div v-else class="rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-base-soft)]/20 py-6 text-center">
                <p class="text-xs text-[var(--color-text-muted)]">No datasets loaded yet.</p>
                <button type="button" class="mt-1 text-xs font-semibold text-[var(--color-accent)] hover:underline" @click="openWorkspaceEditor">Edit workspace to add data →</button>
              </div>
            </div>
          </div>

          <div v-else class="flex flex-1 flex-col items-center justify-center rounded-lg bg-[var(--color-base-soft)] px-5 py-8 text-center">
            <p class="mb-4 text-sm text-[var(--color-text-sub)]">Create a workspace to add context and datasets.</p>
            <button type="button" class="btn-primary px-4 py-2 text-sm" @click="beginInlineCreate">Create your first workspace</button>
          </div>
        </div>

        <div v-else class="flex h-full min-h-0 flex-col">
          <header class="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3 pt-1">
            <button type="button" class="text-xs font-semibold text-[var(--color-accent)] hover:underline" @click="returnToWorkspaceSummary">
              ← Back to workspace summary
            </button>
            <span v-if="isWorkspaceActive" class="inline-flex items-center rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-success)]">Active</span>
          </header>

          <div
            class="min-h-0 flex-1 space-y-4 overflow-y-auto pt-4 scrollbar-thin"
            @dragenter.prevent="handleDropDragEnter"
            @dragover.prevent="handleDropDragOver"
            @dragleave.prevent="handleDropDragLeave"
            @drop.prevent="handleDatasetDrop"
          >
            <section class="space-y-3 border-b border-[var(--color-border)] pb-4">
              <div>
                <h2 class="text-sm font-bold text-[var(--color-text-main)]">{{ editorOpenedAfterCreate ? 'Set up' : 'Edit' }} {{ activeWorkspace?.name || 'workspace' }}</h2>
                <p class="mt-1 text-xs text-[var(--color-text-muted)]">Add context that helps Inquira understand this workspace.</p>
              </div>
              <label class="flex flex-col gap-1.5">
                <span class="section-label">Workspace context <span class="normal-case tracking-normal text-[var(--color-text-muted)]">(Optional)</span></span>
                <textarea v-model="setupWorkspaceContext" rows="4" class="input-base input-outlined resize-none py-1.5 text-xs" placeholder="Describe the business purpose, terms, and schema context for this workspace..." :disabled="isSavingWorkspaceIdentity"></textarea>
              </label>
              <div class="flex items-center justify-between gap-3">
                <span class="text-[10px]" :class="isWorkspaceContextDirty ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'">
                  {{ isWorkspaceContextDirty ? 'Unsaved changes' : 'Saved' }}
                </span>
                <button type="button" class="btn-primary px-4 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-60" :disabled="isSavingWorkspaceIdentity || !isWorkspaceContextDirty" @click="saveWorkspaceContext">
                  {{ isSavingWorkspaceIdentity ? 'Saving...' : 'Save context' }}
                </button>
              </div>
            </section>

            <section class="space-y-3 pb-2">
              <div>
                <p class="section-label">Files</p>
                <p class="mt-1 text-xs text-[var(--color-text-muted)]">Add the datasets used in this workspace.</p>
              </div>

              <button
                type="button"
                class="w-full rounded-xl border border-dashed px-5 py-5 text-center transition-colors disabled:cursor-not-allowed disabled:opacity-70"
                :class="isDropActive
                  ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)]'
                  : 'border-[var(--color-border)] bg-[var(--color-base-soft)]/50 hover:bg-[var(--color-base-soft)]/80'"
                :disabled="isDatasetIngesting || isDeletingDataset || requiresWorkspaceActivation"
                data-testid="workspace-import-datasets-dropzone"
                @click="openDatasetPicker"
              >
                <p class="text-sm font-medium" :class="isDropActive ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'">
                  <template v-if="isDatasetIngesting">Processing dataset...</template>
                  <template v-else-if="requiresWorkspaceActivation">Activate workspace to add files</template>
                  <template v-else-if="isDropActive">Drop files to import them</template>
                  <template v-else>Drop files here or choose files</template>
                </p>
                <p class="mt-1 text-xs text-[var(--color-text-muted)]">CSV, TSV, Parquet, JSON, XLSX, and XLS</p>
              </button>

              <div v-if="isDatasetIngesting" class="rounded-lg px-4 py-3" :class="datasetIngestHasError ? 'bg-[var(--color-danger-bg)]' : 'bg-[var(--color-accent-soft)]'" aria-live="polite">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0"><p class="truncate text-sm font-medium" :class="datasetIngestHasError ? 'text-[var(--color-danger)]' : 'text-[var(--color-accent)]'">{{ datasetIngestFilename || 'Selected dataset' }}</p><p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ datasetIngestStatusLabel }}</p></div>
                  <button v-if="datasetIngestHasError" type="button" class="btn-secondary px-2 py-1 text-xs" @click="retryLastDatasetIngestion">Retry</button>
                  <span v-else class="mt-0.5 h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-accent)]/40 border-t-[var(--color-accent)]"></span>
                </div>
              </div>

              <div v-if="datasetEntries.length" class="space-y-2">
                <div v-for="dataset in datasetEntries" :key="dataset.table_name" class="rounded-lg bg-[var(--color-base-soft)] px-4 py-3">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0"><div class="flex flex-wrap items-center gap-2"><p class="min-w-0 truncate text-sm font-medium text-[var(--color-text-main)]">{{ dataset.filename }}</p><span class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium" :class="datasetSchemaStatusBadgeClass(dataset)">{{ datasetSchemaStatusLabel(dataset) }}</span></div><p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ datasetMetadata(dataset) }}</p></div>
                    <div class="flex items-center gap-1">
                      <button type="button" class="rounded p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]" title="Regenerate schema" :disabled="isDatasetIngesting || isDeletingDataset || isSchemaRegenerateSubmitting" @click="requestRegenerateDatasetSchema(dataset)">↻</button>
                      <button type="button" class="rounded p-1 text-[var(--color-text-muted)] hover:text-[var(--color-danger)]" title="Remove dataset" :disabled="isDatasetIngesting || isDeletingDataset" @click="requestRemoveDataset(dataset)">×</button>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>

    <ConfirmationModal
      :is-open="isDatasetDeleteDialogOpen"
      title="Delete Dataset"
      :message="datasetDeleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeDatasetDeleteDialog"
      @confirm="confirmRemoveDataset"
    />

    <ConfirmationModal
      :is-open="isWorkspaceDeleteDialogOpen"
      title="Delete Workspace"
      :message="workspaceDeleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeWorkspaceDeleteDialog"
      @confirm="deleteWorkspace"
    />

    <ConfirmationModal
      :is-open="isSchemaRegenerateDialogOpen"
      title="Regenerate Schema"
      :message="schemaRegenerateDialogMessage"
      confirm-text="Regenerate"
      cancel-text="Cancel"
      @close="closeSchemaRegenerateDialog"
      @confirm="confirmRegenerateDatasetSchema"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiService } from '../../../services/apiService'
import { previewService } from '../../../services/previewService'
import { settingsWebSocket } from '../../../services/websocketService'
import { useAppStore } from '../../../stores/appStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import ConfirmationModal from '../ConfirmationModal.vue'

const props = defineProps({
  activeWorkspaceId: {
    type: String,
    default: '',
  },
  workspaces: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['select-workspace', 'activate-workspace', 'workspace-operation-change', 'workspace-created'])

const appStore = useAppStore()

const workspaceSummaries = ref({})
const workspaceDetail = ref(null)
const datasetEntries = ref([])
const datasetColumnCounts = ref({})
const datasetFileSizes = ref({})
const isDatasetIngesting = ref(false)
const datasetIngestFilename = ref('')
const datasetIngestMessage = ref('')
const datasetIngestPercent = ref(null)
const datasetIngestError = ref('')
const lastSelectedDatasetPaths = ref([])
const isDatasetDeleteDialogOpen = ref(false)
const pendingRemovalDataset = ref(null)
const isDeletingDataset = ref(false)
const isSchemaRegenerateDialogOpen = ref(false)
const pendingSchemaRegenerateDataset = ref(null)
const isSchemaRegenerateSubmitting = ref(false)
const isRenamingInline = ref(false)
const renameValue = ref('')
const renameInputRef = ref(null)
const isWorkspaceDeleteDialogOpen = ref(false)
const pendingWorkspaceDeletionId = ref('')
const datasetDeletionPollers = new Map()
const datasetIngestionPollers = new Map()
const pendingSchemaReadyNotifications = new Set()
let unsubscribeProgress = null
let unsubscribeRuntimeError = null
let unsubscribeRuntimeComplete = null
let datasetSchemaPoller = null

const isCreatingWorkspace = ref(false)
const isCreatingWorkspaceRuntime = ref(false)
const workspaceCreateMessage = ref('Saving the workspace name. You will add context next.')
const runtimeProgressEntries = ref([])
const runtimeProgressError = ref('')
const runtimeActionMode = ref('')
const isRetryingWorkspaceRuntime = ref(false)
const isHardResettingWorkspaceRuntime = ref(false)
const activeWorkspaceOperation = ref('')
const activeWorkspaceOperationMessage = ref('')
const setupWorkspaceName = ref('')
const setupWorkspaceContext = ref('')
const savedWorkspaceContext = ref('')
const isSavingWorkspaceIdentity = ref(false)
const isCheckingWorkspaceReadiness = ref(false)
const workspaceSurface = ref('summary')
const isInlineCreating = ref(false)
const editorOpenedAfterCreate = ref(false)
const newWorkspaceInputRef = ref(null)
const isDropActive = ref(false)
const dropDepth = ref(0)
const SUPPORTED_DATASET_EXTENSIONS = new Set(['.csv', '.tsv', '.parquet', '.json', '.xlsx', '.xls'])

function normalizeWorkspaceName(value) {
  return String(value || '').toUpperCase()
}

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
const isWorkspaceActive = computed(() => !!activeWorkspace.value && !!activeWorkspace.value.is_active)
const normalizedSetupWorkspaceContext = computed(() => String(setupWorkspaceContext.value || '').trim())
const isWorkspaceContextDirty = computed(() => normalizedSetupWorkspaceContext.value !== String(savedWorkspaceContext.value || '').trim())
const detailWorkspaceSelected = computed(() => Boolean(String(props.activeWorkspaceId || '').trim()))
const requiresWorkspaceActivation = computed(() => !isWorkspaceActive.value)
const detailCreatedAt = computed(() => formatCreatedDate(workspaceDetail.value?.created_at || activeWorkspace.value?.created_at))
const detailConversationCount = computed(() => Number(workspaceDetail.value?.conversation_count || 0))
const detailLastActive = computed(() => formatRelativeTime(workspaceDetail.value?.updated_at || activeWorkspace.value?.updated_at))
const datasetIngestStatusLabel = computed(() => String(datasetIngestMessage.value || 'Processing dataset...').trim() || 'Processing dataset...')
const datasetIngestHasError = computed(() => Boolean(String(datasetIngestError.value || '').trim()))
const workspaceKernelStatus = computed(() => appStore.getWorkspaceKernelStatus(props.activeWorkspaceId))
const workspaceKernelReady = computed(() => ['ready', 'busy'].includes(workspaceKernelStatus.value))
const isRuntimeActionInProgress = computed(() => (
  isCreatingWorkspaceRuntime.value || isRetryingWorkspaceRuntime.value || isHardResettingWorkspaceRuntime.value
))
const runtimeStatusTone = computed(() => {
  if (runtimeProgressError.value) return 'danger'
  if (workspaceKernelReady.value) return 'success'
  if (isRuntimeActionInProgress.value || ['starting', 'connecting'].includes(String(workspaceKernelStatus.value || ''))) {
    return 'accent'
  }
  return 'muted'
})
const runtimeStatusLabel = computed(() => {
  if (runtimeProgressError.value) return 'Runtime failed'
  if (workspaceKernelStatus.value === 'busy') return 'Kernel busy'
  if (workspaceKernelStatus.value === 'ready') return 'Kernel ready'
  if (isHardResettingWorkspaceRuntime.value) return 'Hard reset in progress'
  if (isRetryingWorkspaceRuntime.value) return 'Retry in progress'
  if (isCreatingWorkspaceRuntime.value) return 'Preparing runtime'
  if (workspaceKernelStatus.value === 'starting' || workspaceKernelStatus.value === 'connecting') return 'Starting runtime'
  if (workspaceKernelStatus.value === 'error') return 'Runtime needs attention'
  return 'Runtime not started'
})
const runtimeStatusMessage = computed(() => {
  if (runtimeProgressError.value) return runtimeProgressError.value
  const latestEntry = runtimeProgressEntries.value[runtimeProgressEntries.value.length - 1]
  if (latestEntry?.message) return latestEntry.message
  const fallback = readinessKernelDetail(workspaceKernelStatus.value)
  return fallback === 'Runtime is connected' ? '' : fallback
})
const currentRuntimeProgressMessage = computed(() => {
  const latestEntry = runtimeProgressEntries.value[runtimeProgressEntries.value.length - 1]
  return String(latestEntry?.message || '').trim()
})
const workspaceReadinessItems = computed(() => {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const registeredName = String(activeWorkspace.value?.name || '').trim()
  const context = String(resolveWorkspaceContext()).trim()
  const registered = Boolean(workspaceId && registeredName)
  const active = Boolean(workspaceId && String(appStore.activeWorkspaceId || '').trim() === workspaceId)
  const kernelStatus = String(workspaceKernelStatus.value || 'missing').trim()
  const kernelChecking = isCreatingWorkspaceRuntime.value || isCheckingWorkspaceReadiness.value || ['starting', 'connecting'].includes(kernelStatus)

  return [
    {
      id: 'workspace',
      label: 'Workspace saved',
      detail: registered ? registeredName : 'Waiting for workspace record',
      state: registered ? 'done' : 'pending',
    },
    {
      id: 'context',
      label: 'Context saved',
      detail: context ? 'Shared schema context is ready' : 'No shared context added',
      state: registered ? 'done' : 'pending',
    },
    {
      id: 'active',
      label: 'Workspace active',
      detail: active ? 'New datasets will attach here' : 'Waiting for active workspace',
      state: active ? 'done' : 'pending',
    },
    {
      id: 'kernel',
      label: 'Kernel ready',
      detail: readinessKernelDetail(kernelStatus),
      state: workspaceKernelReady.value ? 'done' : (kernelChecking ? 'checking' : 'pending'),
    },
  ]
})
const workspaceReadinessDoneCount = computed(() => workspaceReadinessItems.value.filter((item) => item.state === 'done').length)
const workspaceReadinessProgress = computed(() => Math.round((workspaceReadinessDoneCount.value / workspaceReadinessItems.value.length) * 100))
const workspaceReadinessComplete = computed(() => workspaceReadinessDoneCount.value === workspaceReadinessItems.value.length)
const workspaceReadinessTitle = computed(() => (
  workspaceReadinessComplete.value
    ? 'Ready for datasets'
    : `${workspaceReadinessDoneCount.value} of ${workspaceReadinessItems.value.length} checks ready`
))
const workspaceReadinessSummary = computed(() => (
  workspaceReadinessComplete.value
    ? 'Workspace setup is saved, active, and connected. Upload datasets when you are ready.'
    : 'Workspace setup is still settling. If the runtime stalls, retry it here before uploading data.'
))
const workspaceCreateTitle = computed(() => 'Creating workspace inside Settings...')
const workspaceDeleteDialogMessage = computed(() => {
  const targetId = String(pendingWorkspaceDeletionId.value || props.activeWorkspaceId || '').trim()
  const target = workspaceCards.value.find((workspace) => workspace.id === targetId)
  const name = String(target?.name || 'this workspace').trim()
  return `Are you sure you want to delete "${name}"? Cleanup will run in the background and cannot be undone.`
})
const datasetDeleteDialogMessage = computed(() => {
  const filename = String(pendingRemovalDataset.value?.filename || '').trim()
  return `Are you sure you want to delete "${filename || 'this dataset'}"? Dataset disappears immediately while storage cleanup continues in background.`
})
const schemaRegenerateDialogMessage = computed(() => {
  const filename = String(pendingSchemaRegenerateDataset.value?.filename || '').trim()
  return `Regenerated schema may differ from the current version because it is generated by the LLM. Continue regenerating "${filename || 'this dataset'}"?`
})
watch(
  () => props.workspaces,
  async () => { await hydrateWorkspaceCards() },
  { deep: true },
)

watch(
  () => setupWorkspaceName.value,
  (nextValue) => {
    const normalized = normalizeWorkspaceName(nextValue)
    if (normalized === nextValue) return
    setupWorkspaceName.value = normalized
  },
)

watch(
  () => props.activeWorkspaceId,
  async () => {
    await loadWorkspaceDetail()
    await loadWorkspaceDatasets()
    await loadActiveDatasetDeletionJobs()
    syncSetupIdentity()
  },
  { immediate: true },
)

onMounted(async () => {
  unsubscribeProgress = settingsWebSocket.subscribeProgress(handleSettingsProgressUpdate)
  unsubscribeRuntimeError = settingsWebSocket.subscribeError(handleRuntimeSocketError)
  unsubscribeRuntimeComplete = settingsWebSocket.subscribeComplete(handleRuntimeSocketComplete)
  await hydrateWorkspaceCards()
  await loadActiveDatasetDeletionJobs()
  syncSetupIdentity()
})

onUnmounted(() => {
  if (typeof unsubscribeProgress === 'function') {
    unsubscribeProgress()
    unsubscribeProgress = null
  }
  if (typeof unsubscribeRuntimeError === 'function') {
    unsubscribeRuntimeError()
    unsubscribeRuntimeError = null
  }
  if (typeof unsubscribeRuntimeComplete === 'function') {
    unsubscribeRuntimeComplete()
    unsubscribeRuntimeComplete = null
  }
  clearWorkspaceOperation()
  stopDatasetDeletionPollers()
  stopDatasetIngestionPollers()
  stopDatasetSchemaPolling()
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

async function selectWorkspaceSummary(workspaceId) {
  workspaceSurface.value = 'summary'
  editorOpenedAfterCreate.value = false
  isInlineCreating.value = false
  await emitSelectedWorkspace(workspaceId)
}

async function beginInlineCreate() {
  workspaceSurface.value = 'summary'
  isInlineCreating.value = true
  setupWorkspaceName.value = ''
  await nextTick()
  newWorkspaceInputRef.value?.focus?.()
}

function cancelInlineCreate() {
  if (isCreatingWorkspace.value) return
  isInlineCreating.value = false
  setupWorkspaceName.value = ''
}

function openWorkspaceEditor() {
  if (!activeWorkspace.value) return
  editorOpenedAfterCreate.value = false
  syncSetupIdentity()
  workspaceSurface.value = 'editor'
}

function returnToWorkspaceSummary() {
  workspaceSurface.value = 'summary'
  editorOpenedAfterCreate.value = false
}

async function emitSelectedWorkspace(workspaceId) {
  const id = String(workspaceId || '').trim()
  if (!id) return
  emit('select-workspace', id)
}

async function activateSelectedWorkspace() {
  const id = String(props.activeWorkspaceId || '').trim()
  if (!id) return
  emit('activate-workspace', id)
}

async function loadWorkspaceDetail() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    workspaceDetail.value = null
    syncSetupIdentity()
    return
  }
  try {
    workspaceDetail.value = await apiService.v1GetWorkspaceSummary(workspaceId)
  } catch {
    workspaceDetail.value = null
  } finally {
    syncSetupIdentity()
  }
}

function resolveWorkspaceContext() {
  return String(workspaceDetail.value?.schema_context ?? activeWorkspace.value?.schema_context ?? '').trim()
}

function syncSetupIdentity() {
  setupWorkspaceName.value = normalizeWorkspaceName(String(activeWorkspace.value?.name || '').trim())
  const context = resolveWorkspaceContext()
  setupWorkspaceContext.value = context
  savedWorkspaceContext.value = context
}

async function saveWorkspaceContext() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  const persisted = await ensureWorkspaceContextPersisted()
  if (persisted) {
    savedWorkspaceContext.value = normalizedSetupWorkspaceContext.value
  }
}

async function ensureWorkspaceNamePersisted({ silent = false } = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || '').trim()
  if (!workspaceId || !name) {
    if (!silent) {
      toast.error('Workspace name required', 'Enter a workspace name to continue.')
    }
    return false
  }

  const currentContext = resolveWorkspaceContext()
  return ensureWorkspaceIdentityPersisted({
    name,
    context: currentContext,
    silent,
    successMessage: 'Workspace name updated.',
  })
}

async function ensureWorkspaceContextPersisted({ silent = false } = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || activeWorkspace.value?.name || '').trim()
  if (!workspaceId || !name) {
    if (!silent) {
      toast.error('Workspace name required', 'Enter a workspace name before saving context.')
    }
    return false
  }
  const context = String(setupWorkspaceContext.value || '').trim()
  return ensureWorkspaceIdentityPersisted({
    name,
    context,
    silent,
    successMessage: 'Workspace context updated.',
  })
}

async function ensureWorkspaceIdentityPersisted({
  name,
  context,
  silent = false,
  successMessage = 'Workspace updated.',
} = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const normalizedName = String(name || '').trim()
  if (!workspaceId || !normalizedName) return false
  const currentName = String(activeWorkspace.value?.name || '').trim()
  const currentContext = resolveWorkspaceContext()
  const unchanged = normalizedName === currentName && context === currentContext
  if (unchanged) return true

  isSavingWorkspaceIdentity.value = true
  try {
    await appStore.renameWorkspace(workspaceId, normalizedName, context)
    await appStore.fetchWorkspaces()
    await loadWorkspaceDetail()
    if (!silent) {
      toast.success('Workspace saved', successMessage)
    }
    return true
  } catch (error) {
    if (!silent) {
      toast.error('Save failed', extractApiErrorMessage(error, 'Failed to save workspace.'))
    } else {
      toast.error('Save failed', extractApiErrorMessage(error, 'Failed to save workspace before continuing.'))
    }
    return false
  } finally {
    isSavingWorkspaceIdentity.value = false
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
      schema_status: String(item?.schema_status || 'queued').trim().toLowerCase(),
      schema_error_message: String(item?.schema_error_message || '').trim(),
      schema_updated_at: String(item?.schema_updated_at || '').trim(),
      filename: formatFilename(item?.source_path || item?.table_name || ''),
    })).filter((item) => item.table_name)
    await enrichDatasetMetadata(workspaceId)
    notifyReadyDatasetSchemas(datasetEntries.value)
    syncDatasetSchemaPolling()
  } catch (error) {
    datasetEntries.value = []
    stopDatasetSchemaPolling()
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to load datasets.'))
  }
}

function startDatasetIngest(path) {
  const normalizedPath = String(path || '').trim()
  isDatasetIngesting.value = true
  datasetIngestFilename.value = formatFilename(normalizedPath)
  datasetIngestMessage.value = 'Preparing dataset ingestion...'
  datasetIngestPercent.value = null
  datasetIngestError.value = ''
}

function appendRuntimeProgress(stage, message) {
  const normalizedMessage = String(message || '').trim()
  if (!normalizedMessage) return
  const previous = runtimeProgressEntries.value[runtimeProgressEntries.value.length - 1]
  if (previous?.message === normalizedMessage) return
  runtimeProgressEntries.value = [
    ...runtimeProgressEntries.value.slice(-7),
    {
      stage: String(stage || '').trim(),
      message: normalizedMessage,
    },
  ]
}

function clearRuntimeProgress({ preserveError = false } = {}) {
  runtimeProgressEntries.value = []
  if (!preserveError) {
    runtimeProgressError.value = ''
  }
}

function resetRuntimeActionFlags() {
  isCreatingWorkspaceRuntime.value = false
  isRetryingWorkspaceRuntime.value = false
  isHardResettingWorkspaceRuntime.value = false
  runtimeActionMode.value = ''
}

function applyDatasetSelectionFromUpload(uploadResult, fallbackPath = '') {
  const resolvedPath = String(uploadResult?.file_path || fallbackPath || '').trim()
  const resolvedTableName = String(uploadResult?.table_name || '').trim()
  const resolvedColumns = Array.isArray(uploadResult?.columns) ? uploadResult.columns : []
  if (!resolvedPath && !resolvedTableName) return

  appStore.setDataFilePath(resolvedPath)
  appStore.setIngestedTableName(resolvedTableName)
  appStore.setIngestedColumns(resolvedColumns)
  appStore.setSchemaFileId(resolvedPath || resolvedTableName)

  window.dispatchEvent(new CustomEvent('dataset-switched', {
    detail: {
      tableName: resolvedTableName || null,
      dataPath: resolvedPath || null,
    },
  }))
}

function dispatchDatasetSchemaReady(dataset) {
  const tableName = String(dataset?.table_name || '').trim()
  if (!tableName) return
  window.dispatchEvent(new CustomEvent('dataset-schema-ready', {
    detail: {
      workspaceId: String(props.activeWorkspaceId || '').trim() || null,
      tableName,
      dataPath: String(dataset?.source_path || '').trim() || null,
    },
  }))
}

function trackSchemaReadyNotificationsFromIngestionJob(job) {
  const items = Array.isArray(job?.items) ? job.items : []
  items.forEach((item) => {
    if (String(item?.status || '').toLowerCase() !== 'completed') return
    const tableName = String(item?.table_name || '').trim()
    if (tableName) {
      pendingSchemaReadyNotifications.add(tableName)
    }
  })
}

function notifyReadyDatasetSchemas(datasets) {
  if (pendingSchemaReadyNotifications.size === 0) return
  const entries = Array.isArray(datasets) ? datasets : []
  entries.forEach((dataset) => {
    const tableName = String(dataset?.table_name || '').trim()
    if (!tableName || !pendingSchemaReadyNotifications.has(tableName)) return
    const status = datasetSchemaStatusState(dataset)
    if (status === 'ready') {
      pendingSchemaReadyNotifications.delete(tableName)
      toast.success('Schema ready', `Schema is ready for ${formatFilename(tableName)}.`)
      dispatchDatasetSchemaReady(dataset)
    } else if (status === 'failed') {
      pendingSchemaReadyNotifications.delete(tableName)
      toast.error('Schema generation failed', dataset?.schema_error_message || `Schema generation failed for ${formatFilename(tableName)}.`)
      dispatchDatasetSchemaReady(dataset)
    }
  })
}

function finishDatasetIngest() {
  isDatasetIngesting.value = false
  datasetIngestFilename.value = ''
  datasetIngestMessage.value = ''
  datasetIngestPercent.value = null
  datasetIngestError.value = ''
  lastSelectedDatasetPaths.value = []
}

function markDatasetIngestFailed(message) {
  isDatasetIngesting.value = true
  datasetIngestError.value = String(message || 'Failed to import dataset.').trim() || 'Failed to import dataset.'
  datasetIngestMessage.value = datasetIngestError.value
  datasetIngestPercent.value = 100
}

function handleSettingsProgressUpdate(data) {
  if (!data || data.type !== 'progress') return
  const stage = String(data?.stage || '').trim().toLowerCase()
  if (stage.startsWith('workspace_runtime')) {
    runtimeProgressError.value = ''
    appendRuntimeProgress(stage, data?.message || '')
    if (isCreatingWorkspace.value) {
      isCreatingWorkspaceRuntime.value = true
      workspaceCreateMessage.value = String(data?.message || '').trim() || 'Preparing workspace runtime...'
    }
    return
  }
  if (!isDatasetIngesting.value) return
  const nextMessage = String(data?.message || '').trim()
  if (nextMessage) {
    datasetIngestMessage.value = nextMessage
  }
  const percent = Number(data?.progress)
  if (Number.isFinite(percent) && percent >= 0 && percent <= 100) {
    datasetIngestPercent.value = Math.round(percent)
  }
}

function handleRuntimeSocketError(message) {
  if (!isRuntimeActionInProgress.value && !isCreatingWorkspace.value) return
  runtimeProgressError.value = String(message || 'Workspace runtime failed.').trim() || 'Workspace runtime failed.'
  appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
  resetRuntimeActionFlags()
}

function handleRuntimeSocketComplete(result) {
  const workspaceId = String(result?.workspace_id || '').trim()
  if (!workspaceId || workspaceId !== String(props.activeWorkspaceId || '').trim()) return
  if (!isRuntimeActionInProgress.value && !isCreatingWorkspace.value) return
  clearRuntimeProgress()
  resetRuntimeActionFlags()
}

function setWorkspaceOperation(operation, message) {
  const normalizedOperation = String(operation || '').trim()
  const normalizedMessage = String(message || 'Workspace setup is still running.').trim()
  activeWorkspaceOperation.value = normalizedOperation
  activeWorkspaceOperationMessage.value = normalizedMessage
  emit('workspace-operation-change', {
    locked: Boolean(normalizedOperation),
    operation: normalizedOperation,
    message: normalizedMessage,
  })
}

function clearWorkspaceOperation() {
  activeWorkspaceOperation.value = ''
  activeWorkspaceOperationMessage.value = ''
  emit('workspace-operation-change', { locked: false, operation: '', message: '' })
}

function notifyWorkspaceOperationBlocked() {
  if (!activeWorkspaceOperation.value) return false
  toast.info(
    'Workspace setup in progress',
    activeWorkspaceOperationMessage.value || 'Wait for the current workspace setup step to finish.',
  )
  return true
}

function readinessKernelDetail(status) {
  const normalized = String(status || '').trim()
  if (normalized === 'ready') return 'Runtime is connected'
  if (normalized === 'busy') return 'Runtime is busy but available'
  if (normalized === 'starting' || normalized === 'connecting') return 'Runtime is starting'
  if (normalized === 'error') return 'Runtime needs attention'
  return 'Runtime not prepared yet'
}

function readinessItemClass(item) {
  const state = String(item?.state || '').trim()
  if (state === 'done') return 'workspace-readiness-item-done'
  if (state === 'checking') return 'workspace-readiness-item-checking'
  return 'workspace-readiness-item-pending'
}

function readinessDotClass(item) {
  const state = String(item?.state || '').trim()
  if (state === 'done') return 'workspace-readiness-dot-done'
  if (state === 'checking') return 'workspace-readiness-dot-checking'
  return 'workspace-readiness-dot-pending'
}

async function refreshWorkspaceReadiness() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || isCheckingWorkspaceReadiness.value) return
  isCheckingWorkspaceReadiness.value = true
  clearRuntimeProgress()
  try {
    const ready = await appStore.ensureWorkspaceKernelConnected(workspaceId)
    if (ready) {
      toast.success('Workspace ready', 'Runtime is ready for dataset uploads.')
    } else {
      toast.error('Runtime not ready', String(appStore.runtimeError || 'Workspace runtime is still starting.'))
    }
  } catch (error) {
    toast.error('Runtime check failed', extractApiErrorMessage(error, 'Failed to prepare workspace runtime.'))
  } finally {
    isCheckingWorkspaceReadiness.value = false
  }
}

async function retryWorkspaceRuntime() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || isRetryingWorkspaceRuntime.value || isHardResettingWorkspaceRuntime.value) return
  clearRuntimeProgress()
  runtimeActionMode.value = 'retry'
  isRetryingWorkspaceRuntime.value = true
  setWorkspaceOperation('runtime', 'Retrying the workspace runtime.')
  appStore.clearWorkspaceKernelStatus(workspaceId)
  try {
    const response = await apiService.v1RetryWorkspaceRuntime(workspaceId)
    await appStore.fetchWorkspaces()
    if (!response?.reset) {
      throw new Error('Workspace runtime retry did not finish successfully.')
    }
    appStore.setWorkspaceKernelStatus(workspaceId, 'ready')
    clearRuntimeProgress()
    toast.success('Runtime ready', 'Workspace runtime restarted successfully.')
  } catch (error) {
    runtimeProgressError.value = extractApiErrorMessage(error, 'Failed to retry workspace runtime.')
    appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
    appStore.setWorkspaceKernelStatus(workspaceId, 'error')
    toast.error('Runtime retry failed', runtimeProgressError.value)
  } finally {
    isRetryingWorkspaceRuntime.value = false
    runtimeActionMode.value = ''
    clearWorkspaceOperation()
  }
}

async function hardResetWorkspaceRuntime() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || isRetryingWorkspaceRuntime.value || isHardResettingWorkspaceRuntime.value) return
  clearRuntimeProgress()
  runtimeActionMode.value = 'hard-reset'
  isHardResettingWorkspaceRuntime.value = true
  setWorkspaceOperation('runtime', 'Rebuilding the workspace runtime from scratch.')
  appStore.clearWorkspaceKernelStatus(workspaceId)
  try {
    const response = await apiService.v1HardResetWorkspaceRuntime(workspaceId)
    await appStore.fetchWorkspaces()
    if (!response?.reset) {
      throw new Error('Workspace hard reset did not finish successfully.')
    }
    appStore.setWorkspaceKernelStatus(workspaceId, 'ready')
    clearRuntimeProgress()
    toast.success('Runtime rebuilt', 'Workspace runtime was rebuilt from scratch.')
  } catch (error) {
    runtimeProgressError.value = extractApiErrorMessage(error, 'Failed to rebuild workspace runtime.')
    appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
    appStore.setWorkspaceKernelStatus(workspaceId, 'error')
    toast.error('Hard reset failed', runtimeProgressError.value)
  } finally {
    isHardResettingWorkspaceRuntime.value = false
    runtimeActionMode.value = ''
    clearWorkspaceOperation()
  }
}

function stopDatasetDeletionPollers() {
  datasetDeletionPollers.forEach((timerId) => clearTimeout(timerId))
  datasetDeletionPollers.clear()
}

function stopDatasetIngestionPollers() {
  datasetIngestionPollers.forEach((timerId) => clearTimeout(timerId))
  datasetIngestionPollers.clear()
}

function trackDatasetDeletionJob(workspaceId, jobId, datasetLabel, timeoutMs = 300000) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const normalizedJobId = String(jobId || '').trim()
  if (!normalizedWorkspaceId || !normalizedJobId) return
  if (datasetDeletionPollers.has(normalizedJobId)) return
  const startedAt = Date.now()
  const displayName = String(datasetLabel || '').trim() || 'dataset'

  const poll = async () => {
    try {
      const job = await apiService.v1GetDatasetDeletionJob(normalizedWorkspaceId, normalizedJobId)
      const status = String(job?.status || '').trim().toLowerCase()
      if (status === 'completed') {
        datasetDeletionPollers.delete(normalizedJobId)
        toast.success('Dataset deletion completed', `"${displayName}" cleanup finished.`)
        return
      }
      if (status === 'failed') {
        datasetDeletionPollers.delete(normalizedJobId)
        const detail = String(job?.error_message || '').trim()
        toast.error('Dataset deletion failed', detail || `Background cleanup failed for "${displayName}".`)
        return
      }
      if (Date.now() - startedAt > timeoutMs) {
        datasetDeletionPollers.delete(normalizedJobId)
        toast.info('Dataset cleanup still running', `Background cleanup for "${displayName}" is still in progress.`)
        return
      }
      const timer = setTimeout(poll, 2000)
      datasetDeletionPollers.set(normalizedJobId, timer)
    } catch (_error) {
      datasetDeletionPollers.delete(normalizedJobId)
    }
  }

  poll()
}

function applyDatasetSelectionFromIngestionJob(job) {
  const items = Array.isArray(job?.items) ? job.items : []
  const firstCompleted = items.find((item) => String(item?.status || '').toLowerCase() === 'completed')
  if (!firstCompleted) return
  applyDatasetSelectionFromUpload({
    file_path: firstCompleted.source_path || '',
    table_name: firstCompleted.table_name || '',
    columns: [],
  }, firstCompleted.source_path || '')
}

function trackDatasetIngestionJob(workspaceId, jobId, timeoutMs = Infinity) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const normalizedJobId = String(jobId || '').trim()
  if (!normalizedWorkspaceId || !normalizedJobId) return
  if (datasetIngestionPollers.has(normalizedJobId)) return
  const startedAt = Date.now()

  const poll = async () => {
    try {
      const job = await apiService.v1GetDatasetIngestionJob(normalizedWorkspaceId, normalizedJobId)
      const status = String(job?.status || '').trim().toLowerCase()
      const completed = Number(job?.completed_count || 0)
      const failed = Number(job?.failed_count || 0)
      const total = Number(job?.total_count || 0)
      if (total > 0) {
        datasetIngestPercent.value = Math.round(((completed + failed) / total) * 100)
      }
      datasetIngestMessage.value = `Processed ${completed + failed} of ${total || '?'} datasets`

      if (['completed', 'completed_with_errors', 'failed'].includes(status)) {
        datasetIngestionPollers.delete(normalizedJobId)
        applyDatasetSelectionFromIngestionJob(job)
        trackSchemaReadyNotificationsFromIngestionJob(job)
        await loadWorkspaceDatasets()
        const failedCount = Number(job?.failed_count || 0)
        datasetIngestPercent.value = 100
        datasetIngestMessage.value = failedCount > 0
          ? `Completed with ${failedCount} failed import${failedCount === 1 ? '' : 's'}.`
          : 'Import complete.'
        await new Promise((resolve) => setTimeout(resolve, 700))
        finishDatasetIngest()
        clearWorkspaceOperation()
        if (status === 'failed' || failedCount > 0) {
          toast.error('Dataset ingestion completed with errors', `${failedCount || 'Some'} file${failedCount === 1 ? '' : 's'} failed to import.`)
        }
        return
      }

      if (Date.now() - startedAt > timeoutMs) {
        datasetIngestionPollers.delete(normalizedJobId)
        finishDatasetIngest()
        clearWorkspaceOperation()
        toast.info('Dataset ingestion still running', 'Dataset import is still running in the background.')
        return
      }
      const timer = setTimeout(poll, 1500)
      datasetIngestionPollers.set(normalizedJobId, timer)
    } catch (error) {
      datasetIngestionPollers.delete(normalizedJobId)
      finishDatasetIngest()
      clearWorkspaceOperation()
      toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to poll dataset ingestion.'))
    }
  }

  poll()
}

async function startBatchDatasetIngestion(paths) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const sourcePaths = Array.isArray(paths)
    ? paths.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (!workspaceId || sourcePaths.length === 0) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before importing datasets.')
    return
  }
  const identityReady = await ensureWorkspaceNamePersisted({ silent: true })
  if (!identityReady) return

  startDatasetIngest(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths.length} selected files`)
  lastSelectedDatasetPaths.value = [...sourcePaths]
  setWorkspaceOperation('ingest', 'Importing selected datasets into the workspace.')
  datasetIngestMessage.value = 'Preparing workspace...'
  try {
    datasetIngestMessage.value = 'Queueing dataset ingestion...'
    const job = await apiService.v1AddDatasetsBatch(workspaceId, sourcePaths)
    const jobId = String(job?.job_id || '').trim()
    if (!jobId) {
      finishDatasetIngest()
      clearWorkspaceOperation()
      toast.error('Dataset Error', 'Backend did not return an ingestion job.')
      return
    }
    trackDatasetIngestionJob(workspaceId, jobId)
  } catch (error) {
    markDatasetIngestFailed(extractApiErrorMessage(error, 'Failed to queue dataset import.'))
    clearWorkspaceOperation()
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to add datasets.'))
  }
}

async function retryLastDatasetIngestion() {
  const paths = Array.isArray(lastSelectedDatasetPaths.value)
    ? lastSelectedDatasetPaths.value.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (!paths.length) {
    toast.info('Retry unavailable', 'Select files again to retry import.')
    finishDatasetIngest()
    return
  }
  await startBatchDatasetIngestion(paths)
}

async function loadActiveDatasetDeletionJobs() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  try {
    const response = await apiService.v1ListDatasetDeletionJobs(workspaceId)
    const jobs = Array.isArray(response?.jobs) ? response.jobs : []
    jobs.forEach((job) => {
      const jobId = String(job?.job_id || '').trim()
      const label = formatFilename(job?.table_name || '')
      trackDatasetDeletionJob(workspaceId, jobId, label)
    })
  } catch (_error) {
    // Ignore hydration errors; explicit delete actions still start polling.
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
  if (!Number.isFinite(bytes) || bytes <= 0) return null
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}

function datasetMetadata(dataset) {
  const segments = [
    `${datasetRowCount(dataset)} rows`,
    `${datasetColumnCount(dataset)} cols`,
  ]
  const sizeLabel = datasetFileSize(dataset)
  if (sizeLabel) {
    segments.push(sizeLabel)
  }
  return segments.join(' · ')
}

function requestRemoveDataset(dataset) {
  if (!dataset || isDeletingDataset.value) return
  pendingRemovalDataset.value = dataset
  isDatasetDeleteDialogOpen.value = true
}

function closeDatasetDeleteDialog({ force = false } = {}) {
  if (isDeletingDataset.value && !force) return
  isDatasetDeleteDialogOpen.value = false
  pendingRemovalDataset.value = null
}

async function confirmRemoveDataset() {
  if (isDeletingDataset.value) return
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const dataset = pendingRemovalDataset.value
  const tableName = String(dataset?.table_name || '').trim()
  const datasetLabel = String(dataset?.filename || formatFilename(tableName)).trim()
  if (!workspaceId || !tableName) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before deleting datasets.')
    return
  }
  isDeletingDataset.value = true
  try {
    const job = await apiService.v1DeleteDataset(workspaceId, tableName)
    const deletedActiveDataset = appStore.handleDatasetRemoved(tableName)
    previewService.clearSchemaCache()
    window.dispatchEvent(new CustomEvent('dataset-switched', { detail: null }))
    await loadWorkspaceDatasets()
    closeDatasetDeleteDialog({ force: true })
    const jobId = String(job?.job_id || '').trim()
    if (jobId) {
      toast.info(
        'Dataset deletion started',
        deletedActiveDataset
          ? 'Dataset removed. Active selection cleared. Background cleanup started.'
          : 'Dataset removed from workspace. Background cleanup started.',
      )
      trackDatasetDeletionJob(workspaceId, jobId, datasetLabel)
    } else {
      toast.success(
        'Dataset removed',
        deletedActiveDataset ? 'Dataset removed. Active selection cleared.' : 'Dataset removed from workspace.',
      )
    }
  } catch (error) {
    toast.error('Remove failed', extractApiErrorMessage(error, 'Failed to remove dataset.'))
  } finally {
    isDeletingDataset.value = false
    if (!isDatasetDeleteDialogOpen.value) {
      pendingRemovalDataset.value = null
    }
  }
}

function requestRegenerateDatasetSchema(dataset) {
  if (!dataset || isSchemaRegenerateSubmitting.value) return
  pendingSchemaRegenerateDataset.value = dataset
  isSchemaRegenerateDialogOpen.value = true
}

function closeSchemaRegenerateDialog() {
  if (isSchemaRegenerateSubmitting.value) return
  isSchemaRegenerateDialogOpen.value = false
  pendingSchemaRegenerateDataset.value = null
}

async function confirmRegenerateDatasetSchema() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const dataset = pendingSchemaRegenerateDataset.value
  const tableName = String(dataset?.table_name || '').trim()
  if (!workspaceId || !tableName) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before generating schemas.')
    return
  }
  try {
    isSchemaRegenerateSubmitting.value = true
    await apiService.v1EnqueueDatasetSchemaRegeneration(workspaceId, tableName)
    await loadWorkspaceDatasets()
    toast.success('Schema regeneration queued', 'Schema generation will continue in the background.')
  } catch (error) {
    toast.error('Schema regeneration failed', extractApiErrorMessage(error, 'Failed to queue schema regeneration.'))
  } finally {
    isSchemaRegenerateSubmitting.value = false
    closeSchemaRegenerateDialog()
  }
}

function getDroppedDatasetPaths(files) {
  return Array.from(files || [])
    .map((file) => {
      const path = String(file?.path || '').trim()
      const lowerPath = path.toLowerCase()
      const extension = lowerPath.includes('.') ? lowerPath.slice(lowerPath.lastIndexOf('.')) : ''
      if (!path || !SUPPORTED_DATASET_EXTENSIONS.has(extension)) return null
      return path
    })
    .filter(Boolean)
}

function handleDropDragEnter() {
  dropDepth.value += 1
  isDropActive.value = true
}

function handleDropDragOver() {
  isDropActive.value = true
}

function handleDropDragLeave() {
  dropDepth.value = Math.max(0, dropDepth.value - 1)
  if (dropDepth.value === 0) {
    isDropActive.value = false
  }
}

async function handleDatasetDrop(event) {
  dropDepth.value = 0
  isDropActive.value = false
  const droppedPaths = getDroppedDatasetPaths(event?.dataTransfer?.files || [])
  if (droppedPaths.length === 0) {
    toast.error('Unsupported Files', 'Drop CSV, TSV, Parquet, JSON, XLSX, or XLS files.')
    return
  }
  await startBatchDatasetIngestion(droppedPaths)
}

async function openDatasetPicker() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before importing datasets.')
    return
  }
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: true,
      filters: [{ name: 'Data files', extensions: ['csv', 'parquet', 'xlsx', 'xls', 'json', 'tsv'] }],
    })
    const selectedPaths = Array.isArray(selected)
      ? selected.map((item) => String(item || '').trim()).filter(Boolean)
      : [String(selected || '').trim()].filter(Boolean)
    await startBatchDatasetIngestion(selectedPaths)
  } catch (error) {
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to add dataset.'))
  }
}

async function startRename() {
  renameValue.value = String(activeWorkspace.value?.name || '').trim()
  isRenamingInline.value = true
  await nextTick()
  renameInputRef.value?.focus?.()
  renameInputRef.value?.select?.()
}

function cancelRename() {
  isRenamingInline.value = false
  renameValue.value = ''
}

async function saveRename() {
  if (!isRenamingInline.value) return
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(renameValue.value || '').trim()
  const currentName = String(activeWorkspace.value?.name || '').trim()
  if (!workspaceId) {
    cancelRename()
    return
  }
  if (!name) {
    cancelRename()
    return
  }
  if (name === currentName) {
    cancelRename()
    return
  }
  try {
    await appStore.renameWorkspace(workspaceId, name, resolveWorkspaceContext())
    await appStore.fetchWorkspaces()
    isRenamingInline.value = false
    renameValue.value = ''
    toast.success('Workspace renamed', 'Workspace name updated.')
  } catch (error) {
    isRenamingInline.value = false
    renameValue.value = ''
    toast.error('Rename failed', extractApiErrorMessage(error, 'Failed to rename workspace.'))
  }
}


function requestDeleteWorkspace(workspaceId) {
  if (notifyWorkspaceOperationBlocked()) return
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  pendingWorkspaceDeletionId.value = normalizedWorkspaceId
  isWorkspaceDeleteDialogOpen.value = true
}

function closeWorkspaceDeleteDialog({ force = false } = {}) {
  if (activeWorkspaceOperation.value === 'delete' && !force) return
  isWorkspaceDeleteDialogOpen.value = false
  pendingWorkspaceDeletionId.value = ''
}

async function deleteWorkspace() {
  const workspaceId = String(pendingWorkspaceDeletionId.value || props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  setWorkspaceOperation('delete', 'Deleting workspace and starting background cleanup.')
  try {
    await appStore.deleteWorkspaceAsync(workspaceId)
    closeWorkspaceDeleteDialog({ force: true })
    await appStore.fetchWorkspaces()
    const fallbackId = String(appStore.activeWorkspaceId || workspaceCards.value[0]?.id || '').trim()
    if (fallbackId) {
      emit('select-workspace', fallbackId)
    }
    workspaceSurface.value = 'summary'
    toast.success('Workspace deletion started', 'Workspace deletion is running in background.')
  } catch (error) {
    toast.error('Delete failed', extractApiErrorMessage(error, 'Failed to delete workspace.'))
  } finally {
    clearWorkspaceOperation()
  }
}

async function createWorkspace() {
  const name = String(setupWorkspaceName.value || '').trim()
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  let workspaceId = ''
  isCreatingWorkspace.value = true
  isCreatingWorkspaceRuntime.value = false
  clearRuntimeProgress()
  runtimeActionMode.value = 'create'
  workspaceCreateMessage.value = 'Saving the workspace name. You will add context next.'
  setWorkspaceOperation('create', 'Creating workspace.')
  try {
    const context = ''
    const workspace = await appStore.createWorkspace(name, context)
    workspaceId = String(workspace?.id || appStore.activeWorkspaceId || '').trim()
    if (!workspaceId) {
      throw new Error('Backend did not return a workspace id.')
    }
    await appStore.fetchWorkspaces()
    emit('workspace-created', {
      workspaceId,
      name,
      context,
    })
    isInlineCreating.value = false
    editorOpenedAfterCreate.value = true
    workspaceSurface.value = 'editor'
    isCreatingWorkspace.value = false
    clearWorkspaceOperation()
    setTimeout(() => {
      void warmWorkspaceRuntimeInBackground(workspaceId)
    }, 0)
  } catch (error) {
    toast.error('Create failed', extractApiErrorMessage(error, 'Failed to create workspace.'))
  } finally {
    isCreatingWorkspace.value = false
    if (!workspaceId) {
      isCreatingWorkspaceRuntime.value = false
      runtimeActionMode.value = ''
    }
    workspaceCreateMessage.value = 'Saving the workspace name. You will add context next.'
    clearWorkspaceOperation()
  }
}

async function warmWorkspaceRuntimeInBackground(workspaceId) {
  const targetWorkspaceId = String(workspaceId || '').trim()
  if (!targetWorkspaceId) return
  clearRuntimeProgress()
  try {
    const ready = await appStore.ensureWorkspaceKernelConnected(targetWorkspaceId)
    if (!ready) {
      runtimeProgressError.value = String(appStore.runtimeError || 'Workspace runtime bootstrap failed.')
      appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
      return
    }
    clearRuntimeProgress()
  } catch (error) {
    runtimeProgressError.value = extractApiErrorMessage(error, 'Workspace runtime bootstrap failed.')
    appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
    appStore.setWorkspaceKernelStatus(targetWorkspaceId, 'error')
  } finally {
    if (runtimeActionMode.value === 'create') {
      runtimeActionMode.value = ''
    }
  }
}

function datasetSchemaStatusState(dataset) {
  const persistedStatus = String(dataset?.schema_status || 'queued').trim().toLowerCase()
  if (['queued', 'generating', 'ready', 'failed'].includes(persistedStatus)) {
    return persistedStatus
  }
  return 'queued'
}

function datasetSchemaStatusLabel(dataset) {
  const status = datasetSchemaStatusState(dataset)
  if (status === 'generating') return 'Generating schema'
  if (status === 'ready') return 'Schema ready'
  if (status === 'failed') return 'Schema failed'
  return 'Schema queued'
}

function datasetSchemaStatusBadgeClass(dataset) {
  const status = datasetSchemaStatusState(dataset)
  if (status === 'generating') return 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
  if (status === 'ready') return 'bg-[var(--color-success-bg)] text-[var(--color-success)]'
  if (status === 'failed') return 'bg-[var(--color-danger-bg)] text-[var(--color-danger)]'
  return 'bg-[var(--color-base-muted)] text-[var(--color-text-muted)]'
}

function stopDatasetSchemaPolling() {
  if (datasetSchemaPoller !== null) {
    clearInterval(datasetSchemaPoller)
    datasetSchemaPoller = null
  }
}

function syncDatasetSchemaPolling() {
  const shouldPoll = datasetEntries.value.some((dataset) => {
    const status = datasetSchemaStatusState(dataset)
    return status === 'queued' || status === 'generating'
  })
  if (!shouldPoll) {
    stopDatasetSchemaPolling()
    return
  }
  if (datasetSchemaPoller !== null) return
  datasetSchemaPoller = setInterval(async () => {
    await loadWorkspaceDatasets()
  }, 1500)
}

function formatFilename(raw) {
  const value = String(raw || '').trim()
  if (!value) return 'dataset'
  const last = value.split('/').pop() || value
  return last
}

function formatCreatedDate(raw) {
  const value = String(raw || '').trim()
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
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

<style scoped>
.workspace-readiness-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 1rem;
  padding: 1rem;
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--color-accent) 14%, transparent), transparent 34%),
    linear-gradient(135deg, color-mix(in srgb, var(--color-base-soft) 92%, var(--color-accent) 8%), var(--color-base));
  box-shadow: 0 14px 34px color-mix(in srgb, var(--color-text-main) 8%, transparent);
  transition:
    border-color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    box-shadow var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-readiness-card::before {
  content: '';
  position: absolute;
  inset: -35% auto auto 54%;
  height: 9rem;
  width: 9rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-accent) 10%, transparent);
  filter: blur(22px);
  pointer-events: none;
}

.workspace-readiness-card-ready {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--color-border));
}

.workspace-readiness-card-pending {
  border-color: color-mix(in srgb, var(--color-accent) 24%, var(--color-border));
}

.workspace-readiness-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.625rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 0.625rem;
  background: color-mix(in srgb, var(--color-base) 72%, transparent);
  transition:
    border-color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-readiness-item:hover {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--color-base) 88%, transparent);
}

.workspace-readiness-item-done {
  border-color: color-mix(in srgb, var(--color-success) 28%, var(--color-border));
}

.workspace-readiness-item-checking {
  border-color: color-mix(in srgb, var(--color-accent) 34%, var(--color-border));
}

.workspace-readiness-item-pending {
  opacity: 0.82;
}

.workspace-readiness-dot {
  display: inline-flex;
  height: 1.5rem;
  width: 1.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  transition:
    background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-readiness-dot-done {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.workspace-readiness-dot-checking {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

.workspace-readiness-dot-pending {
  background: var(--color-base-muted);
  color: var(--color-text-muted);
}

.node-success {
  border-color: color-mix(in srgb, var(--color-success) 30%, transparent);
  background-color: color-mix(in srgb, var(--color-success) 5%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-success) 15%, transparent);
}
.node-danger {
  border-color: color-mix(in srgb, var(--color-danger) 30%, transparent);
  background-color: color-mix(in srgb, var(--color-danger) 5%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-danger) 15%, transparent);
}
.node-accent {
  border-color: color-mix(in srgb, var(--color-accent) 30%, transparent);
  background-color: color-mix(in srgb, var(--color-accent) 5%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-accent) 15%, transparent);
}
</style>
