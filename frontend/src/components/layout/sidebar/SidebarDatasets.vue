<template>
  <div class="flex flex-col w-full">
    <!-- Header -->
    <div 
      class="flex items-center justify-between px-3 py-1.5 group cursor-pointer transition-colors"
      :class="[
        isCollapsed ? 'justify-center hover:bg-zinc-100/50 rounded-lg mx-2 mb-1' : 'hover:bg-zinc-100/50 rounded-md',
        !appStore.hasWorkspace ? 'opacity-50 cursor-not-allowed' : ''
      ]"
      @click="handleHeaderClick"
      title="Datasets"
    >
      <div class="flex items-center gap-2">
        <FolderIcon class="w-3.5 h-3.5" style="color: var(--color-text-muted);" />
        <span
          class="text-[11px] uppercase tracking-[0.08em] font-semibold overflow-hidden whitespace-nowrap transition-[max-width,opacity] duration-200 ease-out"
          :class="isCollapsed ? 'max-w-0 opacity-0' : 'max-w-[120px] opacity-100'"
          style="color: var(--color-text-muted);"
        >Datasets</span>
      </div>
      <button 
        v-if="!isCollapsed && appStore.hasWorkspace"
        @click.stop="openSettings" 
        class="btn-icon transition-opacity"
        :class="datasets.length > 0 ? 'opacity-0 group-hover:opacity-100' : 'opacity-100'"
        title="Add Dataset"
      >
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- List -->
    <Transition name="sidebar-list">
      <div v-show="!isCollapsed && appStore.hasWorkspace" class="flex flex-col mt-0.5 space-y-0.5 pl-6 pr-2 pb-2">
        <div v-if="loading" class="px-2 py-2 text-[11px] text-center flex items-center justify-center gap-2" style="color: var(--color-text-muted);">
          <div class="animate-spin w-3 h-3 border-2 rounded-full" style="border-color: var(--color-border); border-top-color: var(--color-text-muted);"></div>
          <span>Loading datasets...</span>
        </div>

        <div v-else-if="datasets.length === 0" class="px-2 py-2 text-xs text-center" style="color: var(--color-text-muted);">
          No datasets yet. Add in Settings.
        </div>
        
        <div 
          v-for="ds in datasets" 
          :key="ds.table_name"
          class="group/item relative flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors text-xs"
          :class="isSelectedDataset(ds) ? 'bg-green-50/50 text-green-700' : 'text-zinc-500 hover:bg-zinc-100/60 hover:text-zinc-700'"
          @click="selectDataset(ds)"
        >
          <CircleStackIcon class="w-3.5 h-3.5 shrink-0" :class="isSelectedDataset(ds) ? 'text-green-600' : 'text-zinc-400'" />
          <div class="min-w-0">
            <p class="truncate" :class="isSelectedDataset(ds) ? 'font-semibold' : 'font-medium'">
              {{ ds.table_name }}
            </p>
          </div>
        </div>
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
import { 
  FolderIcon,
  CircleStackIcon, 
  PlusIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select', 'open-settings'])

const appStore = useAppStore()
const loading = ref(false)
const datasets = ref([])

const currentDataPath = computed(() => appStore.dataFilePath)

function normalizePath(path) {
  return String(path || '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/\/{2,}/g, '/')
    .toLowerCase()
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

function handleHeaderClick() {
  if (!appStore.hasWorkspace) return
  emit('header-click')
  if (props.isCollapsed) {
    // If it was collapsed, it just expanded, so load datasets
    loadDatasets()
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
  if (!appStore.hasWorkspace || props.isCollapsed) return
  void loadDatasets()
}

// Automatically load datasets when workspace changes
watch(
  () => appStore.hasWorkspace,
  async (hasWorkspace) => {
    if (!hasWorkspace) {
      datasets.value = []
      return
    }
    if (!props.isCollapsed) {
       await loadDatasets()
    }
  }
)

watch(
  () => appStore.activeWorkspaceId,
  async () => {
    if (!appStore.hasWorkspace || props.isCollapsed) {
      datasets.value = []
      return
    }
    await loadDatasets()
  }
)

watch(
  () => props.isCollapsed,
  (collapsed) => {
    if (!collapsed && appStore.hasWorkspace) {
      loadDatasets()
    }
  }
)

watch(
  () => appStore.dataFilePath,
  () => {
    if (!appStore.hasWorkspace || props.isCollapsed) return
    void loadDatasets()
  }
)

onMounted(() => {
  window.addEventListener('dataset-switched', handleDatasetSwitched)
  if (!props.isCollapsed && appStore.hasWorkspace) {
    loadDatasets()
  }
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
