<template>
  <div class="h-full flex flex-col relative">
    <!-- Regeneration Progress Modal Overlay -->
    <Teleport to="body">
      <div v-if="isRegenerating" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
          <!-- Header -->
          <div class="text-center mb-6">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
              <svg class="w-8 h-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900">Generating Schema</h3>
            <p class="text-sm text-gray-500 mt-1">Using AI to analyze your data columns</p>
          </div>

          <!-- Progress Info -->
          <div class="space-y-3">
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-600">{{ regenerationStatus }}</span>
              <span class="text-blue-600 font-medium">{{ formatElapsedTime(elapsedTime) }}</span>
            </div>
            
            <!-- Progress Bar -->
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div 
                class="bg-blue-600 h-2 rounded-full transition-all duration-500"
                :style="{ width: regenerationProgress + '%' }"
              ></div>
            </div>

            <!-- Tips -->
            <p class="text-xs text-gray-400 text-center mt-4">
              💡 The AI is generating meaningful descriptions for each column based on sample data
            </p>
          </div>
        </div>
      </div>
    </Teleport>

    <div class="flex items-center justify-between mb-3">
      <div class="text-sm text-gray-700">Schema Editor</div>
      <div class="flex items-center space-x-2">
        <button @click="refreshSchema" :disabled="schemaLoading" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border disabled:opacity-50">Refresh</button>
        <button @click="regenerateSchema" :disabled="schemaLoading" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border disabled:opacity-50" title="Regenerate schema with AI descriptions">Regenerate</button>
        <button @click="clearCache" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Clear Cache</button>
        <button @click="exportSchema" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Export</button>
        <button @click="saveSchema" :disabled="schemaLoading || !schemaEdited" class="text-sm px-3 py-1.5 bg-blue-600 text-white hover:bg-blue-700 rounded disabled:opacity-50">Save</button>
      </div>
    </div>
    <div class="flex-1 min-h-0 overflow-auto bg-white rounded-lg border p-3">
      <!-- Empty State - No dataset selected -->
      <div v-if="!hasActiveDataset && !schemaLoading" class="flex flex-col items-center justify-center h-full text-center py-12">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
          <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">No Dataset Selected</h3>
        <p class="text-sm text-gray-500 max-w-xs">
          Select a dataset from the dropdown above to view and edit its schema.
        </p>
      </div>
      
      <!-- Loading State -->
      <div v-else-if="schemaLoading && !isRegenerating" class="text-sm text-gray-500">
        Loading schema...
      </div>
      
      <!-- Error State -->
      <div v-else-if="schemaError" class="text-sm text-red-600">{{ schemaError }}</div>
      
      <!-- Schema Content -->
      <div v-else-if="hasActiveDataset">
        <!-- Schema Generating Banner -->
        <div v-if="isSchemaBeingGenerated" class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div class="flex items-center gap-3">
            <div class="flex-shrink-0">
              <svg class="w-5 h-5 text-amber-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <div class="flex-1">
              <h4 class="text-sm font-medium text-amber-800">Schema Generation in Progress</h4>
              <p class="text-xs text-amber-600 mt-0.5">
                AI is analyzing your data to generate meaningful column descriptions. This usually takes 10-30 seconds. 
                The page will automatically refresh when ready.
              </p>
            </div>
          </div>
        </div>
        
        <!-- Data Context/Description -->
        <div v-if="schemaContext" class="mb-4 p-3 bg-gray-50 rounded-lg border">
          <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Data Description</label>
          <textarea 
            v-model="schemaContext" 
            @input="schemaEdited = true"
            class="w-full text-sm text-gray-700 bg-white border rounded px-2 py-1.5 resize-none"
            rows="2"
            placeholder="Describe your data..."
          ></textarea>
        </div>
        
        <!-- Schema Table -->
        <div class="overflow-x-auto w-full">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Column</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(col, i) in schema" :key="i">
                <td class="px-3 py-2 text-sm text-gray-900">{{ col.name }}</td>
                <td class="px-3 py-2 text-sm text-gray-700">
                  <input type="text" class="w-full border rounded px-2 py-1 text-sm" :value="col.description" @input="e => updateSchemaDescription(i, e.target.value)" placeholder="Enter description for this column..." />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { previewService } from '../../services/previewService'
import { apiService } from '../../services/apiService'
import { useAppStore } from '../../stores/appStore'

const appStore = useAppStore()

const schema = ref([])
const schemaContext = ref('')
const schemaLoading = ref(false)
const schemaError = ref('')
const schemaEdited = ref(false)
const isRegenerating = ref(false)

// Computed to check if we have an active dataset
const hasActiveDataset = computed(() => {
  return appStore.dataFilePath && appStore.dataFilePath.trim() !== ''
})

// Computed to check if schema has empty descriptions (being generated in background)
const isSchemaBeingGenerated = computed(() => {
  if (!schema.value || schema.value.length === 0) return false
  // Check if all descriptions are empty and context is empty
  const allEmpty = schema.value.every(col => !col.description || col.description.trim() === '')
  const emptyContext = !schemaContext.value || schemaContext.value.trim() === ''
  return allEmpty && emptyContext
})

// Auto-poll interval for schema refresh when being generated
let schemaPollingInterval = null

// Progress tracking for modal
const regenerationStatus = ref('Initializing...')
const regenerationProgress = ref(0)
const elapsedTime = ref(0)
let timerInterval = null

function startTimer() {
  elapsedTime.value = 0
  timerInterval = setInterval(() => {
    elapsedTime.value += 100
  }, 100)
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function formatElapsedTime(ms) {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`
  }
  return `${remainingSeconds}s`
}

onUnmounted(() => {
  stopTimer()
  stopSchemaPolling()
})

// Auto-poll for schema updates when initially empty
let pollingAttempts = 0
const MAX_POLLING_ATTEMPTS = 20 // Stop after ~60 seconds (20 * 3s)

function startSchemaPolling() {
  if (schemaPollingInterval) return
  pollingAttempts = 0
  console.log('🔄 [Schema] Starting auto-poll for schema updates (max 60s)')
  schemaPollingInterval = setInterval(async () => {
    pollingAttempts++
    
    // Stop if schema generation is complete
    if (!isSchemaBeingGenerated.value) {
      console.log('✅ [Schema] Schema generation complete, stopping poll')
      stopSchemaPolling()
      return
    }
    
    // Stop after max attempts
    if (pollingAttempts >= MAX_POLLING_ATTEMPTS) {
      console.log('⚠️ [Schema] Max polling attempts reached, stopping poll. Click Regenerate to try again.')
      stopSchemaPolling()
      return
    }
    
    console.log(`🔄 [Schema] Polling for updated schema... (attempt ${pollingAttempts}/${MAX_POLLING_ATTEMPTS})`)
    await silentFetchSchema() // Silent refresh without loading state
  }, 3000) // Poll every 3 seconds
}

function stopSchemaPolling() {
  if (schemaPollingInterval) {
    clearInterval(schemaPollingInterval)
    schemaPollingInterval = null
    pollingAttempts = 0
  }
}

// Silent fetch for background polling - doesn't show loading state or clear existing data
async function silentFetchSchema() {
  try {
    const settings = await previewService.getSettings(true)
    if (!settings.data_path) return
    
    const existingSchema = await previewService.loadSchema(settings.data_path, true)
    if (existingSchema && existingSchema.columns) {
      // Check if descriptions are now filled (generation complete)
      const hasDescriptions = existingSchema.columns.some(col => col.description && col.description.trim() !== '')
      if (hasDescriptions || (existingSchema.context && existingSchema.context.trim() !== '')) {
        console.log('✅ [Schema] Poll found completed schema with descriptions!')
        schema.value = existingSchema.columns
        schemaContext.value = existingSchema.context || ''
        stopSchemaPolling()
      }
    }
  } catch (e) {
    console.warn('🔄 [Schema] Silent poll failed:', e)
    // Don't show error - just continue polling
  }
}

async function fetchSchemaData(forceRefresh = false) {
  if (schemaLoading.value) return
  schemaLoading.value = true
  schemaError.value = ''
  schema.value = []
  try {
    const settings = await previewService.getSettings(forceRefresh)
    console.log('📋 [Schema] Settings loaded:', settings.data_path)
    if (!settings.data_path) {
      schemaError.value = 'Please configure your data file path in settings first.'
      return
    }
    try {
      console.log('📋 [Schema] Loading schema for:', settings.data_path, 'forceRefresh:', forceRefresh)
      const existingSchema = await previewService.loadSchema(settings.data_path, forceRefresh)
      console.log('📋 [Schema] Response:', existingSchema)
      if (existingSchema && existingSchema.columns) {
        console.log('📋 [Schema] Loaded', existingSchema.columns.length, 'columns')
        schema.value = existingSchema.columns
        schemaContext.value = existingSchema.context || ''
        
        // Start polling if schema is still being generated
        if (isSchemaBeingGenerated.value) {
          startSchemaPolling()
        }
      } else {
        console.warn('📋 [Schema] No columns in response:', existingSchema)
        schemaError.value = 'Schema has no columns. Try clicking Refresh.'
      }
    } catch (loadError) {
      console.error('📋 [Schema] Failed to load schema:', loadError)
      schemaError.value = `Failed to load schema: ${loadError.message || 'Unknown error'}`
    }
  } catch (e) {
    console.error('📋 [Schema] Failed to get settings:', e)
    schemaError.value = 'Failed to load schema'
  } finally {
    schemaLoading.value = false
  }
}

// Fetch schema for a specific path (used when switching datasets to avoid settings race condition)
async function fetchSchemaDataForPath(dataPath) {
  if (schemaLoading.value || !dataPath) return
  schemaLoading.value = true
  schemaError.value = ''
  schema.value = []
  try {
    console.log('📋 [Schema] Loading schema for path (direct):', dataPath)
    // Force refresh to bypass cache
    const existingSchema = await previewService.loadSchema(dataPath, true)
    console.log('📋 [Schema] Response:', existingSchema)
    if (existingSchema && existingSchema.columns) {
      console.log('📋 [Schema] Loaded', existingSchema.columns.length, 'columns')
      schema.value = existingSchema.columns
      schemaContext.value = existingSchema.context || ''
    } else {
      console.warn('📋 [Schema] No columns in response:', existingSchema)
      schemaError.value = 'Schema has no columns. Try clicking Refresh or Regenerate.'
    }
  } catch (loadError) {
    console.error('📋 [Schema] Failed to load schema:', loadError)
    schemaError.value = `Failed to load schema: ${loadError.message || 'Unknown error'}`
  } finally {
    schemaLoading.value = false
  }
}

function updateSchemaDescription(index, newDescription) {
  if (schema.value[index]) {
    schema.value[index].description = newDescription
    schemaEdited.value = true
  }
}

async function saveSchema() {
  try {
    const settings = await previewService.getSettings()
    if (!settings.data_path) {
      schemaError.value = 'Please configure your data file path in settings first.'
      return
    }
    await apiService.saveSchema(settings.data_path, schemaContext.value || null, schema.value)
    schemaEdited.value = false
    console.log('Schema saved successfully')
  } catch (e) {
    console.error('Failed to save schema:', e)
    schemaError.value = 'Failed to save schema'
  }
}

function refreshSchema() {
  fetchSchemaData(true)
}

async function regenerateSchema() {
  if (schemaLoading.value) return
  schemaLoading.value = true
  schemaError.value = ''
  isRegenerating.value = true
  regenerationStatus.value = 'Initializing...'
  regenerationProgress.value = 0
  startTimer()

  try {
    regenerationStatus.value = 'Loading settings...'
    regenerationProgress.value = 10
    const settings = await previewService.getSettings()
    if (!settings.data_path) {
      schemaError.value = 'Please configure your data file path in settings first.'
      return
    }

    regenerationStatus.value = 'Analyzing data columns with AI...'
    regenerationProgress.value = 30
    console.log('🔄 [Schema] Regenerating schema with LLM for:', settings.data_path)

    // Call generateSchema which uses LLM to create proper descriptions (force=true to regenerate)
    const generatedSchema = await apiService.generateSchema(settings.data_path, null, true)
    console.log('🔄 [Schema] Generated:', generatedSchema)

    if (generatedSchema && generatedSchema.columns) {
      regenerationStatus.value = `Saving ${generatedSchema.columns.length} column descriptions...`
      regenerationProgress.value = 80

      // Save the generated schema
      await apiService.saveSchema(settings.data_path, generatedSchema.context || null, generatedSchema.columns)
      console.log('✅ [Schema] Saved regenerated schema')

      regenerationStatus.value = 'Finalizing...'
      regenerationProgress.value = 95

      // Clear cache and reload
      previewService.clearPreviewCache()
      schema.value = generatedSchema.columns
      schemaContext.value = generatedSchema.context || ''
      
      regenerationProgress.value = 100
      regenerationStatus.value = `✅ Generated ${generatedSchema.columns.length} descriptions!`
      console.log('✅ [Schema] Loaded', generatedSchema.columns.length, 'columns with descriptions')
      
      // Brief pause to show success message
      await new Promise(resolve => setTimeout(resolve, 500))
    } else {
      schemaError.value = 'Failed to generate schema. Please try again.'
    }
  } catch (error) {
    console.error('❌ [Schema] Regeneration failed:', error)
    schemaError.value = `Failed to regenerate schema: ${error.message || 'Unknown error'}`
  } finally {
    stopTimer()
    schemaLoading.value = false
    isRegenerating.value = false
  }
}

// Handle dataset switch event
function handleDatasetSwitch(event) {
  // Get path from event detail, or fallback to appStore
  const newDataPath = event?.detail?.dataPath
  console.log('📢 Dataset switched event:', event)
  console.log('📢 Event detail:', event?.detail)
  console.log('📢 Data path from event:', newDataPath)
  
  schemaEdited.value = false
  schema.value = []
  schemaContext.value = ''
  schemaError.value = ''
  
  // Clear cache to force fresh load from backend
  previewService.clearPreviewCache()
  
  // If event.detail is null, the last dataset was deleted - show empty state
  if (event?.detail === null) {
    console.log('📢 Last dataset deleted - showing empty state')
    return // Let the empty state UI show
  }
  
  // If we have the new path from the event, use it directly
  if (newDataPath) {
    console.log('📢 Using path from event:', newDataPath)
    fetchSchemaDataForPath(newDataPath)
  } else {
    // Fallback: try to get from appStore (should be set before event is dispatched)
    const appStorePath = appStore.dataFilePath
    console.log('📢 No path in event, trying appStore:', appStorePath)
    if (appStorePath) {
      fetchSchemaDataForPath(appStorePath)
    } else {
      // No dataset selected - show empty state
      console.log('📢 No active dataset - showing empty state')
    }
  }
}

onMounted(() => {
  fetchSchemaData()
  window.addEventListener('dataset-switched', handleDatasetSwitch)
})

onUnmounted(() => {
  window.removeEventListener('dataset-switched', handleDatasetSwitch)
})

function clearCache() {
  try {
    previewService.clearPreviewCache()
    console.log('Preview cache cleared')
  } catch (e) {
    console.warn('Failed to clear cache')
  }
}

async function exportSchema() {
  try {
    const settings = await previewService.getSettings()
    if (!settings.data_path) return
    const existingSchema = await previewService.loadSchema(settings.data_path)
    if (!existingSchema || !existingSchema.columns) return
    const blob = new Blob([JSON.stringify(existingSchema, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'schema.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.warn('Failed to export schema')
  }
}
</script>
