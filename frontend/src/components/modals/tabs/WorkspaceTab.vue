<template>
  <section class="scrollbar-hidden h-full overflow-y-auto">
    <div v-if="panelMode === 'ws-list'" class="space-y-4">
      <header class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-bold text-[var(--color-text-main)]">Workspaces</h2>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-md border border-[var(--color-border-strong)] bg-[var(--color-base)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-accent)] shadow-sm transition-all hover:border-[var(--color-accent-border)] hover:bg-[var(--color-accent-soft)] hover:shadow-none"
          @click="emit('navigate', 'ws-create', 'forward')"
        >
          <span class="text-sm leading-none">+</span>
          <span>New workspace</span>
        </button>
      </header>

      <div v-if="workspaceCards.length" class="space-y-2">
        <div
          v-for="workspace in workspaceCards"
          :key="workspace.id"
          class="group w-full cursor-pointer rounded-lg px-3 py-3 text-left transition-all"
          :class="workspace.id === activeWorkspaceId
            ? 'bg-[var(--color-accent-soft)] ring-1 ring-[var(--color-accent-border)]'
            : 'bg-[var(--color-base-soft)] hover:bg-[var(--color-base-muted)]'"
          @click="openWorkspaceDetail(workspace.id)"
        >
          <div class="mb-2 flex items-start justify-between gap-2">
            <p
              class="truncate text-sm font-medium"
              :class="workspace.id === activeWorkspaceId ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'"
            >
              {{ workspace.name || 'Untitled workspace' }}
            </p>
            <div class="flex shrink-0 items-center gap-2">
              <span
                v-if="workspace.id === activeWorkspaceId"
                class="rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[11px] text-[var(--color-success)]"
              >
                Active
              </span>
              <button
                type="button"
                class="rounded p-1.5 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)]"
                title="Delete workspace"
                aria-label="Delete workspace"
                @click.stop="requestDeleteWorkspace(workspace.id)"
              >
                <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M5 7h14" />
                  <path d="M9 7V5h6v2" />
                  <path d="M8 7l1 12h6l1-12" />
                </svg>
              </button>
            </div>
          </div>
          <p class="text-xs text-[var(--color-text-muted)]">
            {{ workspace.conversationCount }} conversations · last active {{ workspace.lastActiveLabel }}
          </p>
        </div>
      </div>

      <div v-else class="rounded-lg bg-[var(--color-base-soft)] px-5 py-8 text-center">
        <svg viewBox="0 0 24 24" class="mx-auto mb-3 h-8 w-8 text-[var(--color-text-muted)]" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M3 7h6l2 2h10v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
        </svg>
        <p class="mb-4 text-sm text-[var(--color-text-sub)]">No workspaces yet</p>
        <button
          type="button"
          class="btn-primary px-4 py-2 text-sm"
          @click="emit('navigate', 'ws-create', 'forward')"
        >
          Create your first workspace
        </button>
      </div>
    </div>

    <div v-else-if="panelMode === 'ws-detail' || panelMode === 'ws-create'" class="flex h-full flex-col">
      <!-- Header -->
      <header class="flex shrink-0 items-center justify-between gap-3 px-4 pt-4">
        <div class="flex min-w-0 flex-1 items-center gap-2">
          <button
            v-if="isCreatingMode"
            type="button"
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] hover:text-[var(--color-text-main)]"
            title="Back to workspace list"
            aria-label="Back to workspace list"
            @click="emit('navigate', 'ws-list', 'backward')"
          >
            <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M12.5 4.5L7 10l5.5 5.5" />
            </svg>
          </button>
          <h2 class="truncate text-base font-semibold text-[var(--color-text-main)]">
            {{ isCreatingMode ? 'New workspace' : (setupWorkspaceName || activeWorkspace?.name || 'Workspace detail') }}
          </h2>
        </div>
        <span
          v-if="!isCreatingMode && isWorkspaceActive"
          class="inline-flex items-center rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-success)]"
        >
          Active
        </span>
      </header>

      <!-- Stepper (single shared instance) -->
      <div class="shrink-0 px-4 pt-5">
        <div class="workspace-stepper">
          <button
            v-for="(step, index) in setupSteps"
            :key="step.id"
            type="button"
            class="workspace-stepper-item"
            @click="goToSetupStep(step.id)"
          >
            <span
              v-if="index > 0"
              class="workspace-stepper-line"
              :class="setupStep > step.id - 1 ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-border)]'"
            ></span>
            <span class="workspace-stepper-dot" :class="stepDotClass(step.id)">{{ step.id }}</span>
            <span class="mt-2 block truncate text-xs font-semibold" :class="stepLabelClass(step.id)">{{ step.label }}</span>
          </button>
        </div>
      </div>

      <!-- Step content -->
      <Transition
        enter-active-class="dialog-fade-enter-active"
        enter-from-class="dialog-fade-enter-from"
        leave-active-class="dialog-fade-leave-active"
        leave-to-class="dialog-fade-leave-to"
        mode="out-in"
        class="min-h-0 flex-1 overflow-y-auto"
      >
        <!-- Step 1: Workspace identity — shared between create and detail -->
        <div v-if="setupStep === 1" key="step-1" class="relative flex flex-col gap-5 px-4 pb-4 pt-2">
          <!-- Loading overlay shown only during creation -->
          <div
            v-if="isCreatingWorkspace"
            class="absolute inset-0 z-10 flex items-center justify-center bg-[var(--color-base)]/85 px-6 text-center backdrop-blur-sm"
            role="status"
            aria-live="polite"
          >
            <div class="max-w-sm">
              <span class="mx-auto mb-4 block h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-accent-border)] border-t-[var(--color-accent)]"></span>
              <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ workspaceCreateTitle }}</p>
              <p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ workspaceCreateMessage }}</p>
            </div>
          </div>

          <p class="rounded-lg bg-[var(--color-base-muted)]/60 px-3 py-2.5 text-sm leading-relaxed text-[var(--color-text-muted)]">
            A workspace is meant for related datasets that share business meaning, terminology, and schema context.
          </p>

          <label class="flex flex-col gap-1.5">
            <span class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Workspace name</span>
            <input
              v-model="setupWorkspaceName"
              type="text"
              class="input-base input-outlined"
              placeholder="e.g. Sales analysis"
              :disabled="isCreatingWorkspace || isSavingWorkspaceIdentity"
            />
          </label>

          <label class="flex flex-col gap-1.5">
            <span class="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
              Workspace context
              <span class="inline-flex items-center gap-1 rounded-md bg-[var(--color-base-muted)] px-1.5 py-0.5 text-[10px] normal-case tracking-normal text-[var(--color-text-muted)]">
                <svg class="h-2.5 w-2.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M8 1v14M1 8h14"/>
                </svg>
                Shared
              </span>
            </span>
            <textarea
              v-model="setupWorkspaceContext"
              :rows="isCreatingMode ? 5 : 3"
              class="input-base input-outlined resize-none"
              placeholder="Describe the business purpose and schema context for this workspace..."
              :disabled="isCreatingWorkspace || isSavingWorkspaceIdentity"
            ></textarea>
          </label>

          <div class="mt-2 flex items-center justify-between border-t border-[var(--color-border)] pt-5">
            <button
              v-if="!isCreatingMode"
              type="button"
              class="btn-ghost text-sm text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)]"
              :disabled="isSavingWorkspaceIdentity"
              @click="requestDeleteWorkspace(activeWorkspaceId)"
            >
              Delete workspace
            </button>
            <span v-else />
            <button
              type="button"
              class="btn-primary px-5 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isCreatingWorkspace || isSavingWorkspaceIdentity || !setupWorkspaceName.trim()"
              @click="continueFromWorkspaceIdentity()"
            >
              <span v-if="isCreatingWorkspace || isSavingWorkspaceIdentity">{{ isCreatingMode ? 'Creating...' : 'Saving...' }}</span>
              <span v-else>Continue</span>
            </button>
          </div>
        </div>

        <!-- Step 2: Select datasets -->
        <div v-else-if="setupStep === 2" key="step-2" class="space-y-4 px-4">
          <section
            class="workspace-readiness-card"
            :class="workspaceReadinessComplete ? 'workspace-readiness-card-ready' : 'workspace-readiness-card-pending'"
            aria-live="polite"
          >
            <div class="relative z-10 flex items-start justify-between gap-4">
              <div class="min-w-0">
                <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-sub)]">Setup readiness</p>
                <h3 class="mt-1 text-base font-semibold text-[var(--color-text-main)]">{{ workspaceReadinessTitle }}</h3>
                <p class="mt-1 text-xs leading-relaxed text-[var(--color-text-muted)]">{{ workspaceReadinessSummary }}</p>
              </div>
              <button
                v-if="!workspaceReadinessComplete"
                type="button"
                class="shrink-0 rounded-md border border-[var(--color-border-strong)] bg-[var(--color-base)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-accent)] shadow-sm transition-all hover:border-[var(--color-accent-border)] hover:bg-[var(--color-accent-soft)] disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="isCheckingWorkspaceReadiness"
                @click="refreshWorkspaceReadiness"
              >
                <span v-if="isCheckingWorkspaceReadiness">Checking...</span>
                <span v-else>Retry runtime</span>
              </button>
            </div>

            <div class="relative z-10 mt-4 h-1.5 overflow-hidden rounded-full bg-[var(--color-base-muted)]">
              <div
                class="h-full rounded-full bg-[var(--color-accent)] transition-[width] duration-500 ease-out"
                :style="{ width: `${workspaceReadinessProgress}%` }"
              ></div>
            </div>

            <div class="relative z-10 mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div
                v-for="item in workspaceReadinessItems"
                :key="item.id"
                class="workspace-readiness-item"
                :class="readinessItemClass(item)"
              >
                <span class="workspace-readiness-dot" :class="readinessDotClass(item)">
                  <svg v-if="item.state === 'done'" viewBox="0 0 16 16" class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3.5 8.5l2.5 2.5 6.5-7" />
                  </svg>
                  <span v-else-if="item.state === 'checking'" class="h-2.5 w-2.5 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
                  <span v-else class="h-1.5 w-1.5 rounded-full bg-current"></span>
                </span>
                <span class="min-w-0">
                  <span class="block truncate text-xs font-semibold text-[var(--color-text-main)]">{{ item.label }}</span>
                  <span class="mt-0.5 block truncate text-[11px] text-[var(--color-text-muted)]">{{ item.detail }}</span>
                </span>
              </div>
            </div>
          </section>

          <div class="rounded-lg bg-[var(--color-base-soft)]/55">
            <div class="flex items-center justify-between px-3 py-2 text-sm">
              <span class="text-[var(--color-text-muted)]">Created date</span>
              <span class="text-[var(--color-text-main)]">{{ detailCreatedAt }}</span>
            </div>
            <div class="flex items-center justify-between px-3 py-2 text-sm">
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

            <div
              v-if="isDatasetIngesting"
              class="rounded-lg px-4 py-3"
              :class="datasetIngestHasError ? 'bg-[var(--color-danger-bg)]' : 'bg-[var(--color-accent-soft)]'"
              aria-live="polite"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium" :class="datasetIngestHasError ? 'text-[var(--color-danger)]' : 'text-[var(--color-accent)]'">{{ datasetIngestFilename || 'Selected dataset' }}</p>
                  <p class="mt-1 text-xs" :class="datasetIngestHasError ? 'text-[var(--color-danger)]/90' : 'text-[var(--color-accent)]/90'">{{ datasetIngestStatusLabel }}</p>
                </div>
                <button
                  v-if="datasetIngestHasError"
                  type="button"
                  class="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-2 py-1 text-xs font-medium text-[var(--color-danger)] transition-colors hover:border-[var(--color-danger)]/45"
                  @click="retryLastDatasetIngestion"
                >
                  Retry
                </button>
                <span v-else class="mt-0.5 h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-accent)]/40 border-t-[var(--color-accent)]"></span>
              </div>
              <div v-if="datasetIngestPercent !== null" class="mt-2">
                <div class="h-1.5 overflow-hidden rounded-full" :class="datasetIngestHasError ? 'bg-[var(--color-danger)]/25' : 'bg-[var(--color-accent-border)]/80'">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="datasetIngestHasError ? 'bg-[var(--color-danger)]' : 'bg-[var(--color-accent)]'"
                    :style="{ width: `${datasetIngestPercent}%` }"
                  ></div>
                </div>
                <p class="mt-1 text-right text-[11px]" :class="datasetIngestHasError ? 'text-[var(--color-danger)]' : 'text-[var(--color-accent)]'">{{ datasetIngestPercent }}%</p>
              </div>
            </div>

            <div v-if="datasetEntries.length" class="space-y-2">
              <div
                v-for="dataset in datasetEntries"
                :key="dataset.table_name"
                class="mb-2 rounded-lg bg-[var(--color-base-soft)] px-4 py-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <p class="min-w-0 truncate text-sm font-medium text-[var(--color-text-main)]">{{ dataset.filename }}</p>
                  <div class="flex items-center gap-1">
                    <button
                      type="button"
                      class="rounded p-1 text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)] disabled:cursor-not-allowed disabled:opacity-50"
                      title="Refresh dataset"
                      :disabled="isDatasetIngesting || isDeletingDataset"
                      @click="refreshDataset(dataset)"
                    >
                      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                        <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                        <path d="M20 4v6h-6" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="rounded p-1 text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)] disabled:cursor-not-allowed disabled:opacity-50"
                      title="Remove dataset"
                      :disabled="isDatasetIngesting || isDeletingDataset"
                      @click="requestRemoveDataset(dataset)"
                    >
                      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                        <path d="M5 7h14" />
                        <path d="M9 7V5h6v2" />
                        <path d="M8 7l1 12h6l1-12" />
                      </svg>
                    </button>
                  </div>
                </div>
                <p class="mt-1 text-xs text-[var(--color-text-muted)]">
                  {{ datasetMetadata(dataset) }}
                </p>
              </div>
            </div>

            <p v-else class="rounded-lg bg-[var(--color-base-soft)] px-3 py-3 text-sm text-[var(--color-text-muted)]">
              No datasets loaded for this workspace.
            </p>

            <button
              type="button"
              class="w-full rounded-lg bg-[var(--color-base-soft)] px-4 py-3 text-center text-sm text-[var(--color-text-muted)] transition-all hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isDatasetIngesting || isDeletingDataset"
              @click="openDatasetPicker"
            >
              <span v-if="isDatasetIngesting">Processing dataset...</span>
              <span v-else>+ Add datasets</span>
            </button>
          </div>
        </div>

        <!-- Step 3: Generate schema -->
        <div v-else key="step-3" class="space-y-4 px-4">
          <div class="rounded-lg bg-[var(--color-base-soft)] px-4 py-4">
            <div class="mb-4 flex items-start justify-between gap-3">
              <div>
                <p class="text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Generate schema</p>
                <p class="mt-1 text-sm text-[var(--color-text-muted)]">Schema descriptions use the shared workspace context for every dataset.</p>
              </div>
              <button
                type="button"
                class="btn-primary px-3 py-2 text-sm whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="isGeneratingWorkspaceSchemas || datasetEntries.length === 0"
                @click="generateWorkspaceSchemas"
              >
                <span v-if="isGeneratingWorkspaceSchemas">Generating...</span>
                <span v-else>Generate all</span>
              </button>
            </div>

            <div v-if="datasetEntries.length" class="space-y-2">
              <div
                v-for="dataset in datasetEntries"
                :key="`schema-${dataset.table_name}`"
                class="flex items-center justify-between gap-3 rounded-lg bg-[var(--color-base)] px-3 py-2"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ dataset.filename }}</p>
                  <p class="truncate text-xs text-[var(--color-text-muted)]">{{ dataset.table_name }}</p>
                </div>
                <span
                  class="shrink-0 rounded-full px-2 py-0.5 text-[11px] border"
                  :class="schemaGenerationClass(dataset.table_name)"
                >
                  {{ schemaGenerationLabel(dataset.table_name) }}
                </span>
              </div>
            </div>
            <p v-else class="rounded-lg bg-[var(--color-base-soft)] px-3 py-3 text-sm text-[var(--color-text-muted)]">
              Add at least one dataset before generating schemas.
            </p>
          </div>
        </div>
      </Transition>
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
  requestedSetupStep: {
    type: Number,
    default: 1,
  },
  workspaceIdentityDraft: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['navigate', 'set-active-workspace', 'workspace-operation-change', 'workspace-created'])

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
const isRenamingInline = ref(false)
const renameValue = ref('')
const renameInputRef = ref(null)
const isWorkspaceDeleteDialogOpen = ref(false)
const pendingWorkspaceDeletionId = ref('')
const datasetDeletionPollers = new Map()
const datasetIngestionPollers = new Map()
let unsubscribeProgress = null

const isCreatingWorkspace = ref(false)
const isCreatingWorkspaceRuntime = ref(false)
const workspaceCreateMessage = ref('Saving the workspace name and shared context. You will move to dataset selection next.')
const activeWorkspaceOperation = ref('')
const activeWorkspaceOperationMessage = ref('')
const setupStep = ref(1)
const setupWorkspaceName = ref('')
const setupWorkspaceContext = ref('')
const isSavingWorkspaceIdentity = ref(false)
const isCheckingWorkspaceReadiness = ref(false)
const isGeneratingWorkspaceSchemas = ref(false)
const schemaGenerationStatuses = ref({})
const setupSteps = [
  { id: 1, label: 'Workspace context' },
  { id: 2, label: 'Select data' },
  { id: 3, label: 'Generate schema' },
]

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
const isCreatingMode = computed(() => props.panelMode === 'ws-create')
const isWorkspaceActive = computed(() => !!activeWorkspace.value && !!activeWorkspace.value.is_active)
const detailCreatedAt = computed(() => formatCreatedDate(workspaceDetail.value?.created_at || activeWorkspace.value?.created_at))
const detailConversationCount = computed(() => Number(workspaceDetail.value?.conversation_count || 0))
const detailLastActive = computed(() => formatRelativeTime(workspaceDetail.value?.updated_at || activeWorkspace.value?.updated_at))
const datasetIngestStatusLabel = computed(() => String(datasetIngestMessage.value || 'Processing dataset...').trim() || 'Processing dataset...')
const datasetIngestHasError = computed(() => Boolean(String(datasetIngestError.value || '').trim()))
const workspaceKernelStatus = computed(() => appStore.getWorkspaceKernelStatus(props.activeWorkspaceId))
const workspaceKernelReady = computed(() => ['ready', 'busy'].includes(workspaceKernelStatus.value))
const workspaceReadinessItems = computed(() => {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const draft = resolveWorkspaceIdentityDraft()
  const registeredName = String(activeWorkspace.value?.name || draft?.name || '').trim()
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
const workspaceCreateTitle = computed(() => (
  isCreatingWorkspaceRuntime.value
    ? 'Preparing workspace runtime inside Settings...'
    : 'Creating workspace inside Settings...'
))
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
watch(
  () => props.panelMode,
  async (nextMode) => {
    if (nextMode === 'ws-list') {
      await hydrateWorkspaceCards()
    }
    if (nextMode === 'ws-detail') {
      await loadWorkspaceDetail()
      await loadWorkspaceDatasets()
      await loadActiveDatasetDeletionJobs()
      syncSetupIdentity()
    }
    if (nextMode === 'ws-create') {
      setupStep.value = 1
      setupWorkspaceName.value = ''
      setupWorkspaceContext.value = ''
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
    await loadActiveDatasetDeletionJobs()
    syncSetupIdentity()
  },
)

watch(
  () => props.requestedSetupStep,
  (nextStep) => {
    if (props.panelMode !== 'ws-detail') return
    const normalized = Number(nextStep)
    if (![1, 2, 3].includes(normalized)) return
    setupStep.value = normalized
  },
  { immediate: true },
)

watch(
  () => props.workspaceIdentityDraft,
  () => {
    if (props.panelMode !== 'ws-detail') return
    syncSetupIdentity()
  },
  { deep: true },
)

watch(
  () => setupStep.value,
  (nextStep) => {
    if (props.panelMode !== 'ws-detail') return
    if (Number(nextStep) !== 1) return
    syncSetupIdentity()
  },
)

onMounted(async () => {
  unsubscribeProgress = settingsWebSocket.subscribeProgress(handleSettingsProgressUpdate)
  if (props.panelMode === 'ws-list') {
    await hydrateWorkspaceCards()
  }
  if (props.panelMode === 'ws-detail') {
    await loadActiveDatasetDeletionJobs()
    syncSetupIdentity()
  }
})

onUnmounted(() => {
  if (typeof unsubscribeProgress === 'function') {
    unsubscribeProgress()
    unsubscribeProgress = null
  }
  clearWorkspaceOperation()
  stopDatasetDeletionPollers()
  stopDatasetIngestionPollers()
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
  const draft = resolveWorkspaceIdentityDraft()
  return String(workspaceDetail.value?.schema_context ?? activeWorkspace.value?.schema_context ?? draft?.context ?? '').trim()
}

function resolveWorkspaceIdentityDraft() {
  const draft = props.workspaceIdentityDraft
  const draftWorkspaceId = String(draft?.workspaceId || '').trim()
  const activeId = String(props.activeWorkspaceId || '').trim()
  if (!draftWorkspaceId || draftWorkspaceId !== activeId) return null
  return {
    name: String(draft?.name || '').trim(),
    context: String(draft?.context || '').trim(),
  }
}

function syncSetupIdentity() {
  if (props.panelMode !== 'ws-detail') return
  const draft = resolveWorkspaceIdentityDraft()
  setupWorkspaceName.value = String(activeWorkspace.value?.name || draft?.name || '').trim()
  setupWorkspaceContext.value = resolveWorkspaceContext()
}

async function goToSetupStep(stepId) {
  if (notifyWorkspaceOperationBlocked()) return
  const normalized = Number(stepId)
  if (![1, 2, 3].includes(normalized)) return
  if (props.panelMode === 'ws-create' && normalized !== 1) {
    await createWorkspace({ setupStep: normalized })
    return
  }
  if (props.panelMode === 'ws-detail' && setupStep.value === 1 && normalized > 1) {
    const persisted = await ensureWorkspaceIdentityPersisted({ silent: true })
    if (!persisted) return
  }
  setupStep.value = normalized
}

async function continueFromWorkspaceIdentity() {
  if (props.panelMode === 'ws-create') {
    await createWorkspace({ setupStep: 2 })
    return
  }
  await saveWorkspaceIdentityAndContinue()
}

async function saveWorkspaceIdentityAndContinue() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || '').trim()
  if (!workspaceId) return
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  const persisted = await ensureWorkspaceIdentityPersisted()
  if (!persisted) return
  setupStep.value = 2
}

async function ensureWorkspaceIdentityPersisted({ silent = false } = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || '').trim()
  if (!workspaceId || !name) {
    if (!silent) {
      toast.error('Workspace name required', 'Enter a workspace name to continue.')
    }
    return false
  }

  const context = String(setupWorkspaceContext.value || '').trim()
  const currentName = String(activeWorkspace.value?.name || '').trim()
  const currentContext = resolveWorkspaceContext()
  const unchanged = name === currentName && context === currentContext
  if (unchanged) return true

  isSavingWorkspaceIdentity.value = true
  try {
    await appStore.renameWorkspace(workspaceId, name, context)
    await appStore.fetchWorkspaces()
    await loadWorkspaceDetail()
    if (!silent) {
      toast.success('Workspace saved', 'Workspace name and context updated.')
    }
    return true
  } catch (error) {
    if (!silent) {
      toast.error('Save failed', extractApiErrorMessage(error, 'Failed to save workspace identity.'))
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
      filename: formatFilename(item?.source_path || item?.table_name || ''),
    })).filter((item) => item.table_name)
    await enrichDatasetMetadata(workspaceId)
  } catch (error) {
    datasetEntries.value = []
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
    if (isCreatingWorkspace.value && props.panelMode === 'ws-create') {
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
        await loadWorkspaceDatasets()
        const failedCount = Number(job?.failed_count || 0)
        const completedCount = Number(job?.completed_count || 0)
        datasetIngestPercent.value = 100
        datasetIngestMessage.value = failedCount > 0
          ? `Completed with ${failedCount} failed import${failedCount === 1 ? '' : 's'}.`
          : 'Import complete.'
        await new Promise((resolve) => setTimeout(resolve, 700))
        finishDatasetIngest()
        if (completedCount > 0) {
          setupStep.value = 3
        }
        clearWorkspaceOperation()
        if (status === 'failed' || failedCount > 0) {
          toast.error('Dataset ingestion completed with errors', `${failedCount || 'Some'} file${failedCount === 1 ? '' : 's'} failed to import.`)
        } else {
          toast.success('Datasets added', `${completedCount} dataset${completedCount === 1 ? '' : 's'} added to workspace.`)
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
  const identityReady = await ensureWorkspaceIdentityPersisted({ silent: true })
  if (!identityReady) return

  startDatasetIngest(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths.length} selected files`)
  lastSelectedDatasetPaths.value = [...sourcePaths]
  setWorkspaceOperation('ingest', 'Importing selected datasets into the workspace.')
  datasetIngestMessage.value = 'Preparing workspace runtime...'
  try {
    const kernelReady = await appStore.ensureWorkspaceKernelConnected(workspaceId)
    if (!kernelReady) {
      throw new Error(String(appStore.runtimeError || 'Workspace runtime bootstrap failed.'))
    }
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
    markDatasetIngestFailed(extractApiErrorMessage(error, 'Backend still initializing. Please retry.'))
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

async function refreshDataset(dataset) {
  const sourcePath = String(dataset?.source_path || '').trim()
  if (!sourcePath || sourcePath.startsWith('browser://')) {
    toast.error('Refresh failed', 'This dataset cannot be refreshed from source.')
    return
  }
  startDatasetIngest(sourcePath)
  setWorkspaceOperation('ingest', 'Refreshing dataset in the workspace.')
  try {
    const uploadResult = await apiService.uploadDataPath(sourcePath)
    applyDatasetSelectionFromUpload(uploadResult, sourcePath)
    await loadWorkspaceDatasets()
    toast.success('Dataset refreshed', 'Dataset refreshed successfully.')
  } catch (error) {
    toast.error('Refresh failed', extractApiErrorMessage(error, 'Failed to refresh dataset.'))
  } finally {
    finishDatasetIngest()
    clearWorkspaceOperation()
  }
}

async function openDatasetPicker() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
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
      emit('set-active-workspace', fallbackId)
    }
    emit('navigate', 'ws-list', 'backward')
    toast.success('Workspace deletion started', 'Workspace deletion is running in background.')
  } catch (error) {
    toast.error('Delete failed', extractApiErrorMessage(error, 'Failed to delete workspace.'))
  } finally {
    clearWorkspaceOperation()
  }
}

async function createWorkspace({ setupStep: targetSetupStep = 2 } = {}) {
  const name = String(setupWorkspaceName.value || '').trim()
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  isCreatingWorkspace.value = true
  isCreatingWorkspaceRuntime.value = false
  workspaceCreateMessage.value = 'Saving the workspace name and shared context. You will move to dataset selection next.'
  setWorkspaceOperation('create', 'Creating workspace and preparing its runtime.')
  try {
    const context = String(setupWorkspaceContext.value || '').trim()
    const workspace = await appStore.createWorkspace(name, context)
    const workspaceId = String(workspace?.id || appStore.activeWorkspaceId || '').trim()
    if (!workspaceId) {
      throw new Error('Backend did not return a workspace id.')
    }
    workspaceCreateMessage.value = 'Preparing workspace runtime...'
    const kernelReady = await appStore.ensureWorkspaceKernelConnected(workspaceId)
    if (!kernelReady) {
      throw new Error(String(appStore.runtimeError || 'Workspace runtime bootstrap failed.'))
    }
    await appStore.fetchWorkspaces()
    emit('workspace-created', {
      workspaceId,
      name,
      context,
      setupStep: targetSetupStep,
    })
    toast.success('Workspace ready', 'Workspace is ready for dataset selection.')
  } catch (error) {
    toast.error('Create failed', extractApiErrorMessage(error, 'Failed to create workspace.'))
  } finally {
    isCreatingWorkspace.value = false
    isCreatingWorkspaceRuntime.value = false
    workspaceCreateMessage.value = 'Saving the workspace name and shared context. You will move to dataset selection next.'
    clearWorkspaceOperation()
  }
}

function schemaGenerationLabel(tableName) {
  const status = String(schemaGenerationStatuses.value?.[tableName]?.status || 'pending').trim()
  if (status === 'running') return 'Generating'
  if (status === 'completed') return 'Generated'
  if (status === 'failed') return 'Failed'
  return 'Pending'
}

function schemaGenerationClass(tableName) {
  const status = String(schemaGenerationStatuses.value?.[tableName]?.status || 'pending').trim()
  if (status === 'running') return 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-transparent'
  if (status === 'completed') return 'bg-[var(--color-success-bg)] text-[var(--color-success)] border-transparent'
  if (status === 'failed') return 'bg-[var(--color-danger-bg)] text-[var(--color-danger)] border-transparent'
  return 'bg-[var(--color-base-muted)] text-[var(--color-text-muted)] border-[var(--color-border)]'
}

function stepDotClass(stepId) {
  if (setupStep.value === stepId) return 'border-[var(--color-accent)] bg-[var(--color-accent)] text-white shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-accent)_20%,transparent)]'
  if (setupStep.value > stepId) return 'border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
  return 'border-[var(--color-border)] bg-[var(--color-base)] text-[var(--color-text-muted)]'
}

function stepLabelClass(stepId) {
  if (setupStep.value === stepId) return 'text-[var(--color-accent)] font-semibold'
  if (setupStep.value > stepId) return 'text-[var(--color-text-main)]'
  return 'text-[var(--color-text-muted)]'
}

async function generateWorkspaceSchemas() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || datasetEntries.value.length === 0) return
  isGeneratingWorkspaceSchemas.value = true
  setWorkspaceOperation('schema', 'Generating workspace schemas from the selected datasets.')
  const context = String(setupWorkspaceContext.value || resolveWorkspaceContext()).trim()
  const nextStatuses = {}
  datasetEntries.value.forEach((dataset) => {
    nextStatuses[dataset.table_name] = { status: 'pending', message: '' }
  })
  schemaGenerationStatuses.value = nextStatuses

  try {
    for (const dataset of datasetEntries.value) {
      const tableName = String(dataset?.table_name || '').trim()
      if (!tableName) continue
      schemaGenerationStatuses.value = {
        ...schemaGenerationStatuses.value,
        [tableName]: { status: 'running', message: '' },
      }
      try {
        await apiService.v1RegenerateDatasetSchema(workspaceId, tableName, { context })
        schemaGenerationStatuses.value = {
          ...schemaGenerationStatuses.value,
          [tableName]: { status: 'completed', message: '' },
        }
      } catch (error) {
        schemaGenerationStatuses.value = {
          ...schemaGenerationStatuses.value,
          [tableName]: { status: 'failed', message: extractApiErrorMessage(error, 'Failed to generate schema.') },
        }
      }
    }

    previewService.clearSchemaCache()
    const failedCount = Object.values(schemaGenerationStatuses.value).filter((item) => item.status === 'failed').length
    if (failedCount > 0) {
      toast.error('Schema generation completed with errors', `${failedCount} dataset${failedCount === 1 ? '' : 's'} failed.`)
    } else {
      toast.success('Schemas generated', 'Workspace schemas generated.')
    }
  } finally {
    isGeneratingWorkspaceSchemas.value = false
    clearWorkspaceOperation()
  }
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

.workspace-stepper {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
}

.workspace-stepper-item {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  color: var(--color-text-muted);
  cursor: pointer;
}

.workspace-stepper-item:focus-visible {
  outline: none;
}

.workspace-stepper-line {
  position: absolute;
  right: 0;
  left: -50%;
  top: 1.25rem;
  height: 1.5px;
  background: var(--color-border);
  transition: background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-stepper-dot {
  position: relative;
  z-index: 1;
  display: inline-flex;
  height: 2.25rem;
  width: 2.25rem;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-border);
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  transition:
    background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    border-color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    box-shadow var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}
</style>
