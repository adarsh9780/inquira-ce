<template>
  <div class="relative">
    <button
      @click="toggleDropdown"
      class="flex items-center space-x-2 px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      :disabled="loading"
    >
      <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
      <span class="max-w-[150px] truncate" :title="currentDatasetName">
        {{ currentDatasetName || 'Select Dataset' }}
      </span>
      <svg class="w-4 h-4 text-gray-400" :class="{ 'rotate-180': isOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Dropdown -->
    <div
      v-if="isOpen"
      class="absolute top-full left-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden"
    >
      <!-- Loading -->
      <div v-if="loading" class="p-3 text-center text-sm text-gray-500">
        <div class="animate-spin inline-block w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full mr-2"></div>
        Loading datasets...
      </div>

      <!-- Empty State -->
      <div v-else-if="datasets.length === 0" class="p-3 text-center">
        <p class="text-sm text-gray-500">No datasets yet</p>
        <p class="text-xs text-gray-400 mt-1">Add data in Settings → Data tab</p>
      </div>

      <!-- Dataset List -->
      <div v-else class="max-h-64 overflow-y-auto">
        <button
          v-for="ds in datasets"
          :key="ds.table_name"
          @click="selectDataset(ds)"
          class="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 transition-colors flex items-center justify-between"
          :class="{ 'bg-blue-50': ds.data_path === currentDataPath }"
        >
          <div class="flex-1 min-w-0">
            <p class="font-medium text-gray-900 truncate" :title="ds.table_name">{{ ds.table_name }}</p>
            <p class="text-xs text-gray-500 truncate" :title="ds.data_path">{{ formatPath(ds.data_path) }}</p>
          </div>
          <svg v-if="ds.data_path === currentDataPath" class="w-4 h-4 text-blue-600 flex-shrink-0 ml-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/appStore'
import { apiService } from '../services/apiService'
import { previewService } from '../services/previewService'

const emit = defineEmits(['open-settings'])

const appStore = useAppStore()
const isOpen = ref(false)
const loading = ref(false)
const datasets = ref([])

const currentDataPath = computed(() => appStore.dataFilePath)
const currentDatasetName = computed(() => {
  if (!currentDataPath.value) return null
  const ds = datasets.value.find(d => d.data_path === currentDataPath.value)
  return ds?.table_name || formatPath(currentDataPath.value)
})

function formatPath(path) {
  if (!path) return ''
  const parts = path.split('/')
  return parts[parts.length - 1]
}

async function loadDatasets() {
  loading.value = true
  try {
    const list = await apiService.listDatasets()
    datasets.value = list || []
  } catch (error) {
    console.error('Failed to load datasets:', error)
    datasets.value = []
  } finally {
    loading.value = false
  }
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    loadDatasets()
  }
}

async function selectDataset(ds) {
  if (ds.data_path === currentDataPath.value) {
    isOpen.value = false
    return
  }

  try {
    // Use simple path update (no reprocessing)
    await apiService.setDataPathSimple(ds.data_path)
    
    // Clear caches first
    previewService.clearPreviewCache()
    
    // Update app store - this also triggers fetchChatHistory
    appStore.setDataFilePath(ds.data_path)
    
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
      detail: { tableName: ds.table_name, dataPath: ds.data_path }
    }))
    
    console.log(`✅ Switched to dataset: ${ds.table_name}`)
  } catch (error) {
    console.error('Failed to switch dataset:', error)
  } finally {
    isOpen.value = false
  }
}

function openSettings() {
  isOpen.value = false
  emit('open-settings')
}

// Close dropdown on outside click
function handleClickOutside(event) {
  const dropdown = event.target.closest('.relative')
  if (!dropdown) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  // Load datasets on mount to show current selection
  loadDatasets()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
