<template>
  <section class="relative">
    <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">Workspace</h2>

    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 -translate-y-1"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div
        v-if="inlineToast"
        class="mb-3 inline-flex items-center gap-2 rounded-full bg-[var(--color-success-bg)] px-3 py-1 text-xs text-[var(--color-success)]"
      >
        <span>✓</span>
        <span>{{ inlineToast }}</span>
      </div>
    </Transition>

    <p
      v-if="inlineError"
      class="mb-3 rounded-lg border border-[var(--color-danger)]/25 bg-[var(--color-base-soft)] px-3 py-2 text-xs text-[var(--color-danger)]"
    >
      {{ inlineError }}
    </p>

    <WorkspaceStepper
      :current-step="currentStep"
      :ws-name="wsName"
      :file-selected="fileSelected"
      :saving-step="savingStep"
      :is-dataset-management-mode="isDatasetManagementMode"
      :datasets="datasetEntries"
      :dataset-column-counts="datasetColumnCounts"
      :dataset-file-sizes="datasetFileSizes"
      :pending-removal-table="pendingRemovalTable"
      :show-compact-dropzone="showCompactDropzone"
      :is-loading-datasets="isLoadingDatasets"
      :is-applying-dataset-action="isApplyingDatasetAction"
      @update:current-step="handleStepChange"
      @update:ws-name="(value) => (wsName = value)"
      @update:file-selected="(value) => (fileSelected = value)"
      @trigger-save="runSave"
      @add-dataset="openDatasetPicker"
      @toggle-compact-dropzone="toggleCompactDropzone"
      @refresh-dataset="refreshDataset"
      @request-remove-dataset="requestRemoveDataset"
      @confirm-remove-dataset="confirmRemoveDataset"
      @cancel-remove-dataset="cancelRemoveDataset"
      @done="closeWorkspaceTab"
    />

    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 translate-y-2"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="showWorkspaceToast"
        class="absolute -bottom-14 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-full bg-[#1C1A18] px-5 py-2.5 text-sm text-white"
      >
        <span class="text-[var(--color-success)]">✓</span>
        <span>Workspace '{{ wsName || 'Untitled' }}' created successfully</span>
      </div>
    </Transition>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import WorkspaceStepper from '../WorkspaceStepper.vue'
import { useAppStore } from '../../../stores/appStore'
import { apiService } from '../../../services/apiService'
import { extractApiErrorMessage } from '../../../utils/apiError'

const props = defineProps({
  initialStep: {
    type: Number,
    default: 1,
  },
  modalOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close-request'])

const appStore = useAppStore()

const currentStep = ref(1)
const wsName = ref('')
const fileSelected = ref(false)
const savingStep = ref(0)
const showWorkspaceToast = ref(false)

const datasetEntries = ref([])
const datasetColumnCounts = ref({})
const datasetFileSizes = ref({})
const pendingRemovalTable = ref('')
const showCompactDropzone = ref(false)
const isLoadingDatasets = ref(false)
const isApplyingDatasetAction = ref(false)
const inlineToast = ref('')
const inlineError = ref('')
const createdWorkspaceId = ref('')

let toastTimer = null
let errorTimer = null

const normalizedInitialStep = computed(() => {
  const parsed = Number(props.initialStep)
  if (!Number.isFinite(parsed)) return 1
  if (parsed < 1) return 1
  if (parsed > 4) return 4
  return Math.floor(parsed)
})

const isDatasetManagementMode = computed(() => normalizedInitialStep.value === 2)

watch(
  () => props.modalOpen,
  async (isOpen) => {
    if (!isOpen) return
    await initializeFlow()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (toastTimer) clearTimeout(toastTimer)
  if (errorTimer) clearTimeout(errorTimer)
})

async function initializeFlow() {
  clearInlineError()
  clearInlineToast()

  currentStep.value = normalizedInitialStep.value
  wsName.value = ''
  fileSelected.value = false
  savingStep.value = 0
  showWorkspaceToast.value = false
  pendingRemovalTable.value = ''
  showCompactDropzone.value = false
  createdWorkspaceId.value = ''

  datasetEntries.value = []
  datasetColumnCounts.value = {}
  datasetFileSizes.value = {}

  if (isDatasetManagementMode.value && !String(appStore.activeWorkspaceId || '').trim()) {
    currentStep.value = 1
    setInlineError('Select or create a workspace before adding datasets.')
    return
  }

  if (currentStep.value >= 2) {
    await loadDatasets()
  }
}

async function handleStepChange(nextStep) {
  const normalizedNext = Math.max(1, Math.min(4, Number(nextStep || 1)))

  if (currentStep.value === 1 && normalizedNext === 2 && !isDatasetManagementMode.value) {
    const ready = await ensureWorkspaceCreatedFromStep1()
    if (!ready) return
    await loadDatasets()
    currentStep.value = 2
    return
  }

  currentStep.value = normalizedNext

  if (normalizedNext === 2) {
    await loadDatasets()
  }
}

async function ensureWorkspaceCreatedFromStep1() {
  if (createdWorkspaceId.value) return true

  const name = String(wsName.value || '').trim()
  if (!name) {
    setInlineError('Workspace name is required.')
    return false
  }

  isApplyingDatasetAction.value = true
  clearInlineError()
  try {
    await appStore.createWorkspace(name)
    createdWorkspaceId.value = String(appStore.activeWorkspaceId || '').trim()
    setInlineToast('Workspace created')
    return true
  } catch (error) {
    setInlineError(extractApiErrorMessage(error, 'Failed to create workspace.'))
    return false
  } finally {
    isApplyingDatasetAction.value = false
  }
}

async function loadDatasets() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    datasetEntries.value = []
    datasetColumnCounts.value = {}
    datasetFileSizes.value = {}
    return
  }

  isLoadingDatasets.value = true
  try {
    const response = await apiService.v1ListDatasets(workspaceId)
    const datasets = Array.isArray(response?.datasets) ? response.datasets : []
    datasetEntries.value = datasets.map((item) => ({
      id: Number(item?.id || 0),
      table_name: String(item?.table_name || '').trim(),
      source_path: String(item?.source_path || '').trim(),
      row_count: Number.isFinite(Number(item?.row_count)) ? Number(item.row_count) : null,
      file_type: String(item?.file_type || '').trim().toLowerCase(),
      updated_at: String(item?.updated_at || '').trim(),
    })).filter((item) => item.table_name)

    await enrichDatasetMetadata(workspaceId, datasetEntries.value)
  } catch (error) {
    datasetEntries.value = []
    datasetColumnCounts.value = {}
    datasetFileSizes.value = {}
    setInlineError(extractApiErrorMessage(error, 'Failed to load datasets.'))
  } finally {
    isLoadingDatasets.value = false
  }
}

async function enrichDatasetMetadata(workspaceId, datasets) {
  const columnCounts = {}
  const fileSizes = {}

  await Promise.all(
    datasets.map(async (dataset) => {
      try {
        const schema = await apiService.v1GetDatasetSchema(workspaceId, dataset.table_name)
        const columns = Array.isArray(schema?.columns) ? schema.columns : []
        columnCounts[dataset.table_name] = columns.length
      } catch {
        columnCounts[dataset.table_name] = null
      }

      try {
        const resolvedSize = await resolveDatasetFileSize(dataset)
        fileSizes[dataset.table_name] = resolvedSize
      } catch {
        fileSizes[dataset.table_name] = null
      }
    }),
  )

  datasetColumnCounts.value = columnCounts
  datasetFileSizes.value = fileSizes
}

async function resolveDatasetFileSize(dataset) {
  const path = String(dataset?.source_path || '').trim()
  if (!path || path.startsWith('browser://')) return null
  if (typeof window === 'undefined' || !window.__TAURI_INTERNALS__) return null

  const { stat } = await import('@tauri-apps/plugin-fs')
  const info = await stat(path)
  const bytes = Number(info?.size || 0)
  return Number.isFinite(bytes) && bytes > 0 ? bytes : null
}

async function openDatasetPicker() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    setInlineError('Select or create a workspace first.')
    return
  }

  clearInlineError()
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [
        { name: 'Data files', extensions: ['csv', 'parquet', 'xlsx', 'xls', 'json', 'tsv'] },
      ],
    })
    const selectedPath = Array.isArray(selected) ? String(selected[0] || '').trim() : String(selected || '').trim()
    if (!selectedPath) return

    await addDatasetFromPath(selectedPath)
  } catch (error) {
    setInlineError(extractApiErrorMessage(error, 'Failed to open file picker.'))
  }
}

async function addDatasetFromPath(path) {
  isApplyingDatasetAction.value = true
  clearInlineError()
  try {
    await apiService.uploadDataPath(path)
    fileSelected.value = true
    showCompactDropzone.value = false
    await loadDatasets()
    setInlineToast('Dataset added')
    window.dispatchEvent(new CustomEvent('dataset-switched'))
  } catch (error) {
    setInlineError(extractApiErrorMessage(error, 'Failed to add dataset.'))
  } finally {
    isApplyingDatasetAction.value = false
  }
}

async function refreshDataset(dataset) {
  const sourcePath = String(dataset?.source_path || '').trim()
  if (!sourcePath || sourcePath.startsWith('browser://')) {
    setInlineError('This dataset cannot be refreshed from a source file.')
    return
  }

  isApplyingDatasetAction.value = true
  clearInlineError()
  try {
    await apiService.uploadDataPath(sourcePath)
    await loadDatasets()
    setInlineToast('Dataset refreshed')
    window.dispatchEvent(new CustomEvent('dataset-switched'))
  } catch (error) {
    setInlineError(extractApiErrorMessage(error, 'Failed to refresh dataset.'))
  } finally {
    isApplyingDatasetAction.value = false
  }
}

function requestRemoveDataset(dataset) {
  pendingRemovalTable.value = String(dataset?.table_name || '').trim()
}

function cancelRemoveDataset() {
  pendingRemovalTable.value = ''
}

async function confirmRemoveDataset(dataset) {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const tableName = String(dataset?.table_name || '').trim()
  if (!workspaceId || !tableName) return

  isApplyingDatasetAction.value = true
  clearInlineError()
  try {
    await apiService.v1DeleteDataset(workspaceId, tableName)
    pendingRemovalTable.value = ''

    if (String(appStore.ingestedTableName || '').trim() === tableName) {
      appStore.setIngestedTableName('')
      appStore.setDataFilePath('')
      appStore.setIngestedColumns([])
    }

    await loadDatasets()
    setInlineToast('Dataset removed')
    window.dispatchEvent(new CustomEvent('dataset-switched'))
  } catch (error) {
    setInlineError(extractApiErrorMessage(error, 'Failed to remove dataset.'))
  } finally {
    isApplyingDatasetAction.value = false
  }
}

function toggleCompactDropzone() {
  showCompactDropzone.value = !showCompactDropzone.value
}

function closeWorkspaceTab() {
  emit('close-request')
}

async function runSave() {
  if (savingStep.value > 0) return

  currentStep.value = 4
  for (let i = 1; i <= 4; i += 1) {
    savingStep.value = i
    await new Promise((resolve) => setTimeout(resolve, i === 3 ? 900 : 600))
  }

  showWorkspaceToast.value = true
  setTimeout(() => {
    showWorkspaceToast.value = false
  }, 2800)
}

function setInlineToast(message) {
  inlineToast.value = String(message || '').trim()
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    inlineToast.value = ''
  }, 1800)
}

function clearInlineToast() {
  inlineToast.value = ''
  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
}

function setInlineError(message) {
  inlineError.value = String(message || '').trim()
  if (errorTimer) clearTimeout(errorTimer)
  errorTimer = setTimeout(() => {
    inlineError.value = ''
  }, 4200)
}

function clearInlineError() {
  inlineError.value = ''
  if (errorTimer) {
    clearTimeout(errorTimer)
    errorTimer = null
  }
}
</script>
