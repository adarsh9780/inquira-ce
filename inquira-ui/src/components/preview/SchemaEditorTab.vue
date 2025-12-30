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
      <div v-if="schemaLoading && !isRegenerating" class="text-sm text-gray-500">
        Loading schema...
      </div>
      <div v-else-if="schemaError" class="text-sm text-red-600">{{ schemaError }}</div>
      <div v-else>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { previewService } from '../../services/previewService'
import { apiService } from '../../services/apiService'

const schema = ref([])
const schemaContext = ref('')
const schemaLoading = ref(false)
const schemaError = ref('')
const schemaEdited = ref(false)
const isRegenerating = ref(false)

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
})

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

onMounted(() => {
  fetchSchemaData()
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
