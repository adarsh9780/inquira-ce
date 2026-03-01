<template>
  <div ref="containerRef" class="relative">
    <button
      @click="toggleDropdown"
      class="flex items-center space-x-2 px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      :disabled="loading || !appStore.hasWorkspace"
      :title="!appStore.hasWorkspace ? 'Create a workspace to enable datasets' : currentDatasetName"
    >
      <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
      <span class="max-w-[150px] truncate" :title="currentDatasetName">
        {{ appStore.hasWorkspace ? (currentDatasetName || 'Select Dataset') : 'Select Workspace First' }}
      </span>
      <svg class="w-4 h-4 text-gray-400" :class="{ 'rotate-180': isOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Dropdown -->
    <div
      v-if="isOpen && appStore.hasWorkspace"
      class="absolute top-full left-0 mt-1 w-96 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden"
    >
      <!-- Loading (Global) -->
      <div v-if="loading" class="p-3 text-center text-sm text-gray-500">
        <div class="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full mr-2"></div>
        {{ loadingMessage }}
      </div>

      <!-- Empty State -->
      <div v-else-if="datasets.length === 0" class="p-3 text-center">
        <p class="text-sm text-gray-500">No datasets yet</p>
        <p class="text-xs text-gray-400 mt-1">Add data in Settings → Data tab</p>
      </div>

      <!-- Dataset List -->
      <div v-else class="max-h-64 overflow-y-auto w-full">
        <div
          v-for="ds in datasets"
          :key="ds.table_name"
          class="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 transition-colors flex items-center justify-between group"
          :class="{ 'bg-blue-50': ds.file_path === currentDataPath }"
        >
          <button 
            @click="selectDataset(ds)"
            class="flex-1 min-w-0 text-left focus:outline-none"
          >
            <p class="font-medium text-gray-900 truncate" :title="ds.table_name">{{ ds.table_name }}</p>
            <!-- Show full path as requested -->
            <p class="text-xs text-gray-500 truncate" :title="ds.file_path">{{ ds.file_path }}</p>
          </button>
          <svg v-if="ds.file_path === currentDataPath" class="w-4 h-4 text-blue-600 flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </div>
      </div>

      <!-- Add New -->
      <div class="border-t border-gray-100 p-2">
        <button
          @click="openSettings"
          class="w-full px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors flex items-center justify-center"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add New Dataset
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../stores/appStore'
import { apiService } from '../services/apiService'
import { previewService } from '../services/previewService'
import { inferTableNameFromDataPath } from '../utils/chatBootstrap'
import { mergeDatasetSources } from '../utils/datasetCatalogMerge'

const emit = defineEmits(['open-settings'])

const appStore = useAppStore()
const containerRef = ref(null)
const isOpen = ref(false)
const loading = ref(false)
const loadingMessage = ref('Loading datasets...')
const datasets = ref([])

const currentDataPath = computed(() => appStore.dataFilePath)
const currentDatasetName = computed(() => {
  if (!currentDataPath.value) return null
  const inferredTableName = inferTableNameFromDataPath(currentDataPath.value)
  if (inferredTableName && datasets.value.some(d => d.table_name === inferredTableName)) {
    return inferredTableName
  }
  return formatPath(currentDataPath.value)
})

function formatPath(path) {
  if (!path) return ''
  const parts = path.split('/')
  const filename = parts[parts.length - 1]
  // Remove file extension for cleaner display
  return filename.replace(/\.[^.]+$/, '')
}

async function loadDatasets() {
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === appStore.activeWorkspaceId)
  if (!activeWorkspace) {
    datasets.value = []
    return
  }
  loading.value = true
  loadingMessage.value = 'Loading datasets...'
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
      // Hide datasets living entirely in the browser storage
      return !path.startsWith('browser://') && !path.startsWith('browser:/') && !path.startsWith('/browser:/')
    })
  } catch (error) {
    console.error('Failed to load datasets:', error)
    datasets.value = []
  } finally {
    loading.value = false
  }
}

function toggleDropdown() {
  if (!appStore.hasWorkspace) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    loadDatasets()
  }
}

async function selectDataset(ds) {
  if (ds.file_path === currentDataPath.value) {
    isOpen.value = false
    return
  }

  try {
    let selectedPath = ds.file_path
    let selectedTableName = (ds.table_name || inferTableNameFromDataPath(ds.file_path || '')).trim()

    // Ensure workspace catalog/table state is hydrated before preview/schema refresh.
    if (appStore.activeWorkspaceId && ds.file_path && !String(ds.file_path).startsWith('browser://')) {
      const syncedDataset = await apiService.v1AddDataset(appStore.activeWorkspaceId, ds.file_path)
      selectedPath = syncedDataset?.source_path || selectedPath
      selectedTableName = (syncedDataset?.table_name || selectedTableName).trim()
    }

    // Clear caches first
    previewService.clearSchemaCache()

    // Update local workspace-scoped dataset selection state.
    appStore.setDataFilePath(selectedPath)
    appStore.setIngestedTableName(selectedTableName)
    appStore.setIngestedColumns([])
    appStore.setSchemaFileId(selectedPath || selectedTableName)
    
    // Clear code/results from previous dataset
    appStore.setGeneratedCode('')
    appStore.setPythonFileContent('')
    appStore.setResultData(null)
    appStore.setPlotlyFigure(null)
    appStore.setDataframes([])
    appStore.setFigures([])
    appStore.setScalars([])
    appStore.setTerminalOutput('')
    
    // Emit custom event for other components (e.g., SchemaEditorTab) to refresh
    window.dispatchEvent(new CustomEvent('dataset-switched', { 
      detail: { tableName: selectedTableName, dataPath: selectedPath }
    }))

    console.debug(`✅ Switched to dataset: ${selectedTableName}`)
  } catch (error) {
    console.error('Failed to switch dataset:', error)
  } finally {
    isOpen.value = false
  }
}

function openSettings() {
  isOpen.value = false
  emit('open-settings', 'data') // Open directly to Data tab
}

// Close dropdown on outside click
function handleClickOutside(event) {
  // If click is outside this component's container, close the dropdown
  if (containerRef.value && !containerRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  if (appStore.hasWorkspace) {
    loadDatasets()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(
  () => appStore.hasWorkspace,
  async (hasWorkspace) => {
    if (!hasWorkspace) {
      isOpen.value = false
      datasets.value = []
      return
    }
    await loadDatasets()
  }
)
</script>
