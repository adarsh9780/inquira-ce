<template>
  <div class="flex flex-col w-full">
    <!-- Header -->
    <div 
      class="flex items-center justify-between px-3 py-2 group cursor-pointer transition-colors"
      :class="[
        isCollapsed ? 'justify-center hover:bg-zinc-100/50 rounded-lg mx-2 mb-1' : 'hover:bg-zinc-100/50',
        !appStore.hasWorkspace ? 'opacity-50 cursor-not-allowed' : ''
      ]"
      @click="handleHeaderClick"
      title="Datasets"
    >
      <div class="flex items-center gap-2">
        <CircleStackIcon class="w-4 h-4 text-gray-500 transition-transform" :class="!isCollapsed && 'scale-110 text-gray-700'" />
        <span v-if="!isCollapsed" class="text-xs font-semibold text-gray-600 uppercase tracking-wider">Datasets</span>
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
    <div v-show="!isCollapsed && appStore.hasWorkspace" class="flex flex-col mt-0.5 space-y-0.5 px-2 pb-2">
      <div v-if="loading" class="px-2 py-2 text-[11px] text-center text-gray-400 flex items-center justify-center gap-2">
        <div class="animate-spin w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full"></div>
        <span>Loading datasets...</span>
      </div>

      <div v-else-if="datasets.length === 0" class="px-2 py-2 text-xs text-center text-gray-400">
        No datasets yet. Add in Settings.
      </div>
      
      <div 
        v-for="ds in datasets" 
        :key="ds.table_name"
        class="group/item relative flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer transition-colors border"
        :class="ds.file_path === currentDataPath ? 'bg-zinc-100/80 border-zinc-200' : 'hover:bg-zinc-100/50 border-transparent'"
        @click="selectDataset(ds)"
      >
        <div class="flex items-start gap-2 min-w-0 pr-2 pt-0.5">
          <CheckCircleIcon 
            v-if="ds.file_path === currentDataPath" 
            class="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" 
          />
          <div v-else class="w-3.5 h-3.5 shrink-0 mt-0.5"></div>
          <div class="flex-1 min-w-0">
             <p class="truncate text-xs" :class="ds.file_path === currentDataPath ? 'font-medium text-blue-800' : 'text-gray-700'">
              {{ ds.table_name }}
            </p>
            <p v-if="ds.file_path !== currentDataPath" class="text-[10px] text-gray-400 truncate">{{ formatPath(ds.file_path) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { apiService } from '../../../services/apiService'
import { previewService } from '../../../services/previewService'
import { inferTableNameFromDataPath } from '../../../utils/chatBootstrap'
import { mergeDatasetSources } from '../../../utils/datasetCatalogMerge'
import { 
  CircleStackIcon, 
  PlusIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select', 'open-settings'])

const appStore = useAppStore()
const loading = ref(false)
const datasets = ref([])

const currentDataPath = computed(() => appStore.dataFilePath)

function formatPath(path) {
  if (!path) return ''
  const parts = path.split('/')
  const filename = parts[parts.length - 1]
  return filename.replace(/\.[^.]+$/, '')
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
  if (ds.file_path === currentDataPath.value) {
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
    appStore.setScalars([])
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
  () => props.isCollapsed,
  (collapsed) => {
    if (!collapsed && appStore.hasWorkspace) {
      loadDatasets()
    }
  }
)

onMounted(() => {
  if (!props.isCollapsed && appStore.hasWorkspace) {
    loadDatasets()
  }
})
</script>
