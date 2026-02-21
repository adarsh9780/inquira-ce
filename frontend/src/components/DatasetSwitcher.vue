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
            class="flex-1 min-w-0 text-left focus:outline-none pr-2"
          >
            <p class="font-medium text-gray-900 truncate" :title="ds.table_name">{{ ds.table_name }}</p>
            <!-- Show full path as requested -->
            <p class="text-xs text-gray-500 truncate" :title="ds.file_path">{{ ds.file_path }}</p>
          </button>
          
          <div class="flex items-center space-x-1">
            <svg v-if="ds.file_path === currentDataPath" class="w-4 h-4 text-blue-600 flex-shrink-0 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            
            <!-- Refresh Button -->
            <button 
              @click.stop="promptRefresh(ds)"
              class="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
              title="Refresh Dataset"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            
            <!-- Delete Button -->
            <button 
              @click.stop="promptDelete(ds)"
              class="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
              title="Delete Dataset"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
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

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6" @click.stop>
        <div class="flex items-center space-x-3 text-red-600 mb-4">
          <div class="p-2 bg-red-100 rounded-full">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-gray-900">Delete Dataset?</h3>
        </div>
        
        <p class="text-gray-600 mb-6">
          Are you sure you want to delete <strong>{{ datasetToDelete?.table_name }}</strong>?
          <br><br>
          <span class="text-sm text-gray-500">
            This will permanently remove:
            <ul class="list-disc list-inside mt-1 ml-1">
              <li>The DuckDB table</li>
              <li>Schema file (schema.json)</li>
              <li>Preview cache files</li>
            </ul>
          </span>
        </p>

        <div class="flex justify-end space-x-3">
          <button 
            @click="closeDeleteModal"
            class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            :disabled="loading"
          >
            Cancel
          </button>
          
          <button 
            @click="confirmDelete"
            class="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 flex items-center"
            :disabled="loading"
          >
            <span v-if="loading" class="mr-2 animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
            {{ loading ? 'Deleting...' : 'Delete Dataset' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Refresh Confirmation Modal -->
    <div v-if="showRefreshModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6" @click.stop>
        <div class="flex items-center space-x-3 text-blue-600 mb-4">
          <div class="p-2 bg-blue-100 rounded-full">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-gray-900">Refresh Dataset?</h3>
        </div>
        
        <p class="text-gray-600 mb-6">
          Refresh <strong>{{ datasetToRefresh?.table_name }}</strong> from source file?
          <br><br>
          <span class="text-sm text-gray-500">
            This will:
            <ul class="list-disc list-inside mt-1 ml-1">
              <li>Reimport data from the original file</li>
              <li>Regenerate the schema with AI</li>
              <li>Create a backup (restored if refresh fails)</li>
            </ul>
          </span>
        </p>

        <div class="flex justify-end space-x-3">
          <button 
            @click="closeRefreshModal"
            class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            :disabled="loading"
          >
            Cancel
          </button>
          
          <button 
            @click="confirmRefresh"
            class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
            :disabled="loading"
          >
            <span v-if="loading" class="mr-2 animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
            {{ loading ? 'Refreshing...' : 'Refresh Dataset' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../stores/appStore'
import { apiService } from '../services/apiService'
import { previewService } from '../services/previewService'
import { duckdbService } from '../services/duckdbService'
import { buildBrowserDataPath, inferTableNameFromDataPath } from '../utils/chatBootstrap'
import { mergeDatasetSources } from '../utils/datasetCatalogMerge'

const emit = defineEmits(['open-settings'])

const appStore = useAppStore()
const containerRef = ref(null)
const isOpen = ref(false)
const loading = ref(false)
const loadingMessage = ref('Loading datasets...')
const datasets = ref([])

// Delete modal state
const showDeleteModal = ref(false)
const datasetToDelete = ref(null)

// Refresh modal state
const showRefreshModal = ref(false)
const datasetToRefresh = ref(null)

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
    let runtimeTables = []
    try {
      runtimeTables = await duckdbService.getTableNames()
    } catch (_err) {
      runtimeTables = []
    }
    datasets.value = mergeDatasetSources({
      catalogDatasets,
      runtimeTables,
      currentDataPath: currentDataPath.value
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

// Prompt for delete - opens modal
function promptDelete(ds) {
  datasetToDelete.value = ds
  showDeleteModal.value = true
}

function closeDeleteModal() {
  showDeleteModal.value = false
  datasetToDelete.value = null
}

async function confirmDelete() {
  if (!datasetToDelete.value) return
  const { toast } = await import('../composables/useToast.js')
  closeDeleteModal()
  toast.info('Not Available Yet', 'Dataset deletion is not part of the v1 workspace API yet.')
}

// Prompt for refresh - opens modal
function promptRefresh(ds) {
  datasetToRefresh.value = ds
  showRefreshModal.value = true
}

function closeRefreshModal() {
  showRefreshModal.value = false
  datasetToRefresh.value = null
}

async function confirmRefresh() {
  if (!datasetToRefresh.value) return
  const { toast } = await import('../composables/useToast.js')
  closeRefreshModal()
  toast.info('Not Available Yet', 'Dataset refresh is not part of the v1 workspace API yet.')
}

async function selectDataset(ds) {
  if (ds.file_path === currentDataPath.value) {
    isOpen.value = false
    return
  }

  try {
    // Clear caches first
    previewService.clearPreviewCache()

    // Update local workspace-scoped dataset selection state.
    appStore.setDataFilePath(ds.file_path)
    const tableName = (ds.table_name || inferTableNameFromDataPath(ds.file_path || '')).trim()
    appStore.setIngestedTableName(tableName)
    appStore.setIngestedColumns([])
    appStore.setSchemaFileId(buildBrowserDataPath(tableName))
    
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
      detail: { tableName: ds.table_name, dataPath: ds.file_path }
    }))
    
    console.debug(`✅ Switched to dataset: ${ds.table_name}`)
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
  // If a modal is open, ignore click-outside
  if (showDeleteModal.value || showRefreshModal.value) return

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
