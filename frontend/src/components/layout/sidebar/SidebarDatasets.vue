<template>
  <div class="flex flex-col w-full">
    <div
      class="flex items-center justify-between w-full py-2 transition-colors"
      :class="!appStore.hasWorkspace ? 'opacity-50 cursor-not-allowed' : 'hover:bg-zinc-100/60'"
      @click="toggleExpanded"
    >
      <div class="flex items-center gap-2 min-w-0">
        <ChevronRightIcon
          class="w-3.5 h-3.5 shrink-0 transition-transform duration-200"
          :class="isExpanded ? 'rotate-90' : ''"
          style="color: var(--color-text-muted);"
        />
        <FolderIcon class="w-3.5 h-3.5 shrink-0" style="color: var(--color-text-muted);" />
        <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">
          Datasets
        </span>
      </div>
      <button
        v-if="appStore.hasWorkspace"
        @click.stop="openSettings"
        class="btn-icon shrink-0"
        title="Add Dataset"
      >
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <Transition name="sidebar-list">
      <div
        v-show="isExpanded && appStore.hasWorkspace"
        class="flex flex-col mt-1 space-y-0.5 pl-4 pb-2"
        @dragenter.prevent="handleDropDragEnter"
        @dragover.prevent="handleDropDragOver"
        @dragleave.prevent="handleDropDragLeave"
        @drop.prevent="handleDatasetDrop"
      >
        <div
          v-if="isDropActive"
          class="rounded-lg border-2 border-dashed px-3 py-4 text-center text-xs"
          style="border-color: var(--color-border-hover); color: var(--color-text-main); background-color: color-mix(in srgb, var(--color-surface) 78%, transparent);"
        >
          Drop CSV, Parquet, Excel, JSON, or TSV files to add them to this workspace.
        </div>

        <div v-if="loading" class="px-2 py-2 text-[11px] text-center flex items-center justify-center gap-2" style="color: var(--color-text-muted);">
          <div class="animate-spin w-3 h-3 border-2 rounded-full" style="border-color: var(--color-border); border-top-color: var(--color-text-muted);"></div>
          <span>Loading datasets...</span>
        </div>

        <div
          v-else-if="datasets.length === 0"
          class="px-2 py-3 text-xs"
          style="color: var(--color-text-muted);"
        >
          This workspace does not have any datasets yet.
        </div>

        <button
          v-for="ds in datasets"
          :key="ds.table_name"
          type="button"
          class="group/item relative flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors text-xs"
          :class="isSelectedDataset(ds) ? 'bg-emerald-50 text-emerald-800' : 'text-zinc-600 hover:bg-zinc-100/60 hover:text-zinc-800'"
          @click="selectDataset(ds)"
        >
          <CircleStackIcon class="w-3.5 h-3.5 shrink-0" :class="isSelectedDataset(ds) ? 'text-emerald-600' : 'text-zinc-400'" />
          <div class="min-w-0 flex-1">
            <p class="truncate" :class="isSelectedDataset(ds) ? 'font-semibold' : 'font-medium'">
              {{ ds.table_name }}
            </p>
            <p v-if="ds.file_path" class="truncate text-[10px]" :class="isSelectedDataset(ds) ? 'text-emerald-700/70' : 'text-zinc-400'">
              {{ datasetCaption(ds.file_path) }}
            </p>
          </div>
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { apiService } from '../../../services/apiService'
import { previewService } from '../../../services/previewService'
import { inferTableNameFromDataPath } from '../../../utils/chatBootstrap'
import { mergeDatasetSources } from '../../../utils/datasetCatalogMerge'
import { toast } from '../../../composables/useToast'
import {
  ChevronRightIcon,
  FolderIcon,
  CircleStackIcon,
  PlusIcon,
} from '@heroicons/vue/24/outline'

defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select', 'open-settings'])

const appStore = useAppStore()
const loading = ref(false)
const datasets = ref([])
const isDropActive = ref(false)
const dropDepth = ref(0)
const isExpanded = ref(true)

const SUPPORTED_DATASET_EXTENSIONS = new Set(['.csv', '.tsv', '.parquet', '.json', '.xlsx', '.xls'])

const currentDataPath = computed(() => appStore.dataFilePath)

function normalizePath(path) {
  return String(path || '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/\/{2,}/g, '/')
    .toLowerCase()
}

function datasetCaption(path) {
  const normalized = String(path || '').trim().replace(/\\/g, '/')
  if (!normalized) return ''
  const parts = normalized.split('/').filter(Boolean)
  return parts.slice(-2).join('/')
}

function isSelectedDataset(ds) {
  const datasetPath = normalizePath(ds?.file_path)
  const activePath = normalizePath(currentDataPath.value)
  if (datasetPath && activePath && datasetPath === activePath) return true

  const datasetTable = String(ds?.table_name || '').trim().toLowerCase()
  const activeTable = String(appStore.ingestedTableName || '').trim().toLowerCase()
  return Boolean(datasetTable && activeTable && datasetTable === activeTable)
}

async function loadDatasets() {
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === appStore.activeWorkspaceId)
  if (!activeWorkspace) {
    datasets.value = []
    return
  }
  loading.value = true
  try {
    const response = await apiService.v1ListDatasets(activeWorkspace.id)
    const workspaceDatasets = response?.datasets || []
    const catalogDatasets = workspaceDatasets.map((item) => ({
      ...item,
      file_path: item.source_path,
    }))
    datasets.value = mergeDatasetSources({
      catalogDatasets,
      runtimeTables: [],
      currentDataPath: currentDataPath.value
    }).filter(ds => {
      const path = String(ds.file_path || '').toLowerCase()
      return !path.startsWith('browser://') && !path.startsWith('browser:/') && !path.startsWith('/browser:/')
    })
  } catch (error) {
    console.error('Failed to load datasets:', error)
    datasets.value = []
  } finally {
    loading.value = false
  }
}

function toggleExpanded() {
  if (!appStore.hasWorkspace) return
  isExpanded.value = !isExpanded.value
  if (isExpanded.value) {
    emit('header-click')
    void loadDatasets()
  }
}

async function selectDataset(ds) {
  if (isSelectedDataset(ds)) {
    emit('select')
    return
  }
  try {
    let selectedPath = ds.file_path
    let selectedTableName = (ds.table_name || inferTableNameFromDataPath(ds.file_path || '')).trim()

    if (appStore.activeWorkspaceId && ds.file_path && !String(ds.file_path).startsWith('browser://')) {
      const syncedDataset = await apiService.v1AddDataset(appStore.activeWorkspaceId, ds.file_path)
      selectedPath = syncedDataset?.source_path || selectedPath
      selectedTableName = (syncedDataset?.table_name || selectedTableName).trim()
    }

    previewService.clearSchemaCache()

    appStore.setDataFilePath(selectedPath)
    appStore.setIngestedTableName(selectedTableName)
    appStore.setIngestedColumns([])
    appStore.setSchemaFileId(selectedPath || selectedTableName)

    appStore.setGeneratedCode('')
    appStore.setPythonFileContent('')
    appStore.setResultData(null)
    appStore.setPlotlyFigure(null)
    appStore.setDataframes([])
    appStore.setFigures([])
    appStore.setTerminalOutput('')

    window.dispatchEvent(new CustomEvent('dataset-switched', {
      detail: { tableName: selectedTableName, dataPath: selectedPath }
    }))

    emit('select')
  } catch (error) {
    console.error('Failed to switch dataset:', error)
  }
}

function openSettings() {
  emit('open-settings', 'data')
}

function handleDatasetSwitched() {
  if (!appStore.hasWorkspace || !isExpanded.value) return
  void loadDatasets()
}

function getDroppedDatasetPaths(files) {
  return Array.from(files || [])
    .map((file) => {
      const path = String(file?.path || '')
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
  if (!appStore.activeWorkspaceId) {
    toast.error('Workspace Required', 'Create or select a workspace before dropping datasets.')
    return
  }

  const droppedPaths = getDroppedDatasetPaths(event?.dataTransfer?.files || [])
  if (droppedPaths.length === 0) {
    toast.error('Unsupported Files', 'Drop CSV, Parquet, Excel, JSON, or TSV files.')
    return
  }

  const successes = []
  const failures = []

  for (const path of droppedPaths) {
    try {
      const result = await apiService.uploadDataPath(path)
      successes.push(result)
    } catch (error) {
      failures.push({ path, error })
    }
  }

  if (successes.length > 0) {
    const last = successes[successes.length - 1]
    await loadDatasets()
    if (last?.file_path) {
      await selectDataset({
        file_path: last.file_path,
        table_name: last.table_name,
      })
    }
    toast.success(
      'Datasets Added',
      failures.length > 0
        ? `${successes.length} file(s) added. ${failures.length} file(s) failed.`
        : `${successes.length} file(s) added to this workspace.`
    )
  }

  if (failures.length > 0 && successes.length === 0) {
    toast.error('Dataset Import Failed', 'None of the dropped files could be added.')
  }
}

watch(
  () => appStore.hasWorkspace,
  async (hasWorkspace) => {
    if (!hasWorkspace) {
      datasets.value = []
      return
    }
    if (isExpanded.value) {
      await loadDatasets()
    }
  }
)

watch(
  () => appStore.activeWorkspaceId,
  async () => {
    if (!appStore.hasWorkspace) {
      datasets.value = []
      return
    }
    isExpanded.value = true
    await loadDatasets()
  }
)

onMounted(() => {
  if (appStore.hasWorkspace && isExpanded.value) {
    void loadDatasets()
  }
  window.addEventListener('dataset-switched', handleDatasetSwitched)
})

onUnmounted(() => {
  window.removeEventListener('dataset-switched', handleDatasetSwitched)
})
</script>

<style scoped>
.sidebar-list-enter-active,
.sidebar-list-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.sidebar-list-enter-from,
.sidebar-list-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
