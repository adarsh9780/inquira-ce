<template>
  <div class="p-6">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
      <DocumentArrowUpIcon class="w-6 h-6 mr-2 text-blue-600" />
      Data Configuration
    </h2>

    <!-- API Key Warning -->
    <div v-if="!hasApiKey" class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
      <div class="flex items-center">
        <ExclamationTriangleIcon class="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" />
        <div class="flex-1">
          <p class="text-sm text-yellow-800">
            <strong>API Key Required:</strong> Please set your API key in the API tab first before configuring data settings.
          </p>
        </div>
      </div>
    </div>

    <!-- Progress Indicator -->
    <div v-if="isProcessing" class="mb-4">
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div class="flex items-center space-x-3 mb-2">
          <div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
          <span class="text-sm font-medium text-blue-900">{{ progressMessage }}</span>
        </div>
        <div class="w-full bg-blue-200 rounded-full h-2">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-300"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>
        <p class="text-xs text-blue-600 mt-2">{{ formatElapsedTime(elapsedTime) }}</p>
      </div>
    </div>

    <!-- Update Status Banner -->
    <div class="mb-4" v-if="!isProcessing && (isCheckingUpdate || updateInfo)">
      <div
        :class="[
          'rounded-lg p-4 border',
          isCheckingUpdate ? 'bg-blue-50 border-blue-200' : (updateNeeded ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200')
        ]"
      >
        <div class="flex items-start">
          <div class="mt-0.5 mr-2">
            <div v-if="isCheckingUpdate" class="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent"></div>
            <ExclamationTriangleIcon v-else-if="updateNeeded" class="h-5 w-5 text-yellow-600" />
            <CheckCircleIcon v-else class="h-5 w-5 text-green-600" />
          </div>
          <div class="flex-1">
            <p class="text-sm font-medium" :class="updateNeeded ? 'text-yellow-900' : (isCheckingUpdate ? 'text-blue-900' : 'text-green-900')">
              <span v-if="isCheckingUpdate">Checking if data re-creation is needed…</span>
              <span v-else-if="updateNeeded">Update recommended: database re-creation may be needed</span>
              <span v-else>Data is up to date. No re-creation needed</span>
            </p>
            <div v-if="!isCheckingUpdate && updateInfo && updateInfo.reasons && updateInfo.reasons.length" class="mt-1">
              <p class="text-xs text-yellow-800">Reasons:</p>
              <ul class="mt-1 text-xs text-yellow-800 list-disc list-inside">
                <li v-for="(r, idx) in updateInfo.reasons" :key="idx">{{ r }}</li>
              </ul>
            </div>
            <p v-if="!isCheckingUpdate && updateInfo && updateInfo.dataset_updated_at" class="text-xs text-gray-600 mt-1">
              Last updated: {{ updateInfo.dataset_updated_at }}
            </p>
          </div>
          <div class="ml-3 flex items-center space-x-3">
            <button
              v-if="!isCheckingUpdate && updateNeeded && !isProcessing"
              @click="rebuildNow"
              class="text-xs px-2 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700"
            >
              Rebuild now
            </button>
            <button v-if="!isCheckingUpdate" @click="checkForUpdate" class="text-xs text-blue-600 hover:text-blue-700">Recheck</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Success/Error Messages -->
    <div v-if="message" :class="messageTypeClass" class="mb-4 p-3 rounded-md flex items-center">
      <CheckCircleIcon v-if="messageType === 'success'" class="w-5 h-5 mr-2 flex-shrink-0" />
      <ExclamationTriangleIcon v-else class="w-5 h-5 mr-2 flex-shrink-0" />
      <span class="text-sm">{{ message }}</span>
    </div>

    <div class="space-y-6">
      <!-- Data File Path Input -->
      <div>
        <label for="data-file-input" class="block text-sm font-medium text-gray-700 mb-2">
          Data File
        </label>
        <div class="max-w-md">
          <div class="flex items-center space-x-2">
            <button
              type="button"
              @click="openFilePicker"
              class="flex-1 flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm cursor-pointer hover:bg-gray-50 transition-colors text-left"
              :class="{ 'opacity-50 cursor-not-allowed': isProcessing || isPickingFile || isRestoringFile }"
              :disabled="isProcessing || isPickingFile || isRestoringFile"
            >
              <svg class="w-5 h-5 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span v-if="!appStore.dataFilePath" class="text-gray-500">Choose a file...</span>
              <span v-else class="text-gray-900 truncate">{{ appStore.dataFilePath }}</span>
            </button>
            <input
              id="data-file-input"
              ref="fileInputRef"
              type="file"
              accept=".csv,.parquet,.xlsx,.json,.tsv"
              @change="handleFileSelected"
              :disabled="isProcessing || isPickingFile || isRestoringFile"
              class="hidden"
            />
            <span v-if="isPickingFile" class="inline-flex items-center text-sm text-blue-600">
              <div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent mr-2"></div>
              Ingesting…
            </span>
            <span v-if="isRestoringFile" class="inline-flex items-center text-sm text-blue-600">
              <div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent mr-2"></div>
              Restoring…
            </span>
          </div>
        </div>
        <p class="mt-1 text-xs text-gray-500">
          Supported formats: CSV, Parquet, Excel (.xlsx), JSON, TSV
        </p>
        <p v-if="canPersistHandles" class="mt-1 text-xs text-gray-500">
          File access is remembered for this browser profile, so reloads can restore automatically.
        </p>
        <p v-if="ingestedColumns.length" class="mt-1 text-xs text-green-600">
          ✅ {{ ingestedColumns.length }} columns loaded into DuckDB
        </p>
      </div>

      <!-- Schema Context Input -->
      <div>
        <label for="schema-context" class="block text-sm font-medium text-gray-700 mb-2">
          Data Domain Context
        </label>
        <textarea
          id="schema-context"
          :value="appStore.schemaContext"
          @input="handleSchemaContextChange"
          :disabled="isProcessing"
          placeholder="Describe your data domain to help generate better schema descriptions (e.g., 'This dataset contains customer information for an e-commerce platform including purchase history, demographics, and behavioral data')"
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
          rows="4"
        ></textarea>
        <p class="mt-1 text-xs text-gray-500">
          This context will be used to generate more accurate schema descriptions for your data columns.
        </p>
      </div>
    </div>

    <!-- Save Button -->
    <div class="mt-8 pt-4 border-t border-gray-200 space-y-3">
      <button
        @click="saveDataSettings"
        :disabled="!hasApiKey || isProcessing || !appStore.dataFilePath.trim()"
        class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <span v-if="isProcessing" class="inline-flex items-center">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
          Processing...
        </span>
        <span v-else>Save Data Settings</span>
      </button>
      
      <!-- Refresh Data Button (only show when data is configured) -->
      <button
        v-if="appStore.dataFilePath.trim() && !isProcessing"
        @click="refreshCurrentDataset"
        :disabled="isRefreshing"
        class="w-full px-4 py-2 bg-gray-100 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
      >
        <svg class="w-4 h-4 mr-2" :class="{ 'animate-spin': isRefreshing }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span>{{ isRefreshing ? 'Refreshing...' : 'Refresh Data from Source' }}</span>
      </button>
    </div>
  </div>

  <!-- Fullscreen Processing Overlay - Blocks all UI interaction -->
  <Teleport to="body">
    <div v-if="isProcessing" class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div class="bg-white rounded-xl shadow-2xl p-8 max-w-lg w-full mx-4">
        <!-- Header -->
        <div class="text-center mb-6">
          <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
            <svg class="w-8 h-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-gray-900">Processing Data</h3>
          <p class="text-sm text-gray-500 mt-1">{{ progressMessage }}</p>
        </div>

        <!-- Progress Bar -->
        <div class="space-y-3">
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div 
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
          <div class="flex justify-between text-sm text-gray-600">
            <span>{{ progressPercent }}%</span>
            <span>{{ formatElapsedTime(elapsedTime) }}</span>
          </div>
        </div>

        <!-- Warning -->
        <div class="mt-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div class="flex items-start">
            <ExclamationTriangleIcon class="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" />
            <div>
              <p class="text-sm font-medium text-yellow-800">Do not close or refresh this page</p>
              <p class="text-xs text-yellow-700 mt-1">Interrupting this process may corrupt your data and require reprocessing.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { apiService } from '../../services/apiService'
import { settingsWebSocket } from '../../services/websocketService'
import { previewService } from '../../services/previewService'
import { toast } from '../../composables/useToast'
import {
  DocumentArrowUpIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

// Declare emits
const emit = defineEmits(['dataSaved'])

const appStore = useAppStore()

// State
const isProcessing = ref(false)
const isCheckingUpdate = ref(false)
const lastUpdateCheck = ref(null)
const updateInfo = ref(null) // stores the response from /settings/check-update
const progressMessage = ref('')
const progressPercent = ref(0)
const elapsedTime = ref(0)
const message = ref('')
const messageType = ref('') // 'success' | 'error'
const timerInterval = ref(null)
const startTime = ref(null)
const isPickingFile = ref(false)
const isRefreshing = ref(false)
const isRestoringFile = ref(false)
const ingestedColumns = ref([])  // columns from DuckDB-WASM ingestion
const ingestedTableName = ref('') // DuckDB table name
const fileInputRef = ref(null)   // ref for the <input type="file">

// Computed
const hasApiKey = computed(() => appStore.apiKey.trim() !== '')

const updateNeeded = computed(() => {
  return !!(updateInfo.value && updateInfo.value.should_update === true)
})


const messageTypeClass = computed(() => {
  return messageType.value === 'success'
    ? 'bg-green-50 border border-green-200 text-green-800'
    : 'bg-red-50 border border-red-200 text-red-800'
})

// Timer functions
function startTimer() {
  startTime.value = Date.now()
  elapsedTime.value = 0
  timerInterval.value = setInterval(() => {
    elapsedTime.value = Date.now() - startTime.value
  }, 100)
}

function stopTimer() {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
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

// Progress functions
function showProgress(message, percent = 0) {
  isProcessing.value = true
  progressMessage.value = message
  progressPercent.value = percent
}

function updateProgress(message, percent) {
  progressMessage.value = message
  progressPercent.value = percent
}

function hideProgress() {
  isProcessing.value = false
  progressMessage.value = ''
  progressPercent.value = 0
  stopTimer()
}

// Message functions
function showMessage(text, type) {
  message.value = text
  messageType.value = type
}

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

// File picker — uses Tauri native dialog or falls back to <input type="file">
async function openFilePicker() {
  // Try Tauri native dialog first
  if (window.__TAURI_INTERNALS__) {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog')
      const filePath = await open({
        filters: [{ name: 'Data', extensions: ['csv', 'parquet', 'xlsx', 'json', 'tsv', 'duckdb'] }]
      })
      if (filePath) {
        await processSelectedPath(filePath)
      }
      return
    } catch (err) {
      console.error('Tauri dialog failed, falling back:', err)
    }
  }
  // Browser fallback
  fileInputRef.value?.click()
}

async function handleFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  await processSelectedFileUpload(file)
  event.target.value = ''
}

// Tauri path: send the absolute file path to backend
async function processSelectedPath(filePath) {
  clearMessage()
  isPickingFile.value = true
  try {
    const result = await apiService.uploadDataPath(filePath)
    appStore.setDataFilePath(filePath)
    ingestedTableName.value = result.table_name || filePath.split('/').pop().split('.')[0]
    ingestedColumns.value = result.columns || []
    appStore.setIngestedColumns(ingestedColumns.value)
    appStore.setIngestedTableName(ingestedTableName.value)
    appStore.setSchemaFileId(filePath)
    showMessage(`Loaded "${filePath.split('/').pop()}" → table "${ingestedTableName.value}" (${result.row_count || '?'} rows, ${ingestedColumns.value.length} columns)`, 'success')
  } catch (error) {
    console.error('File path loading failed:', error)
    showMessage(`Failed to load file: ${error.message}`, 'error')
  } finally {
    isPickingFile.value = false
  }
}

// Browser fallback: upload the File object to backend
async function processSelectedFileUpload(file) {
  clearMessage()
  isPickingFile.value = true
  try {
    const result = await apiService.uploadFile(file)
    appStore.setDataFilePath(result.file_path || file.name)
    ingestedTableName.value = result.table_name || file.name.split('.')[0]
    ingestedColumns.value = result.columns || []
    appStore.setIngestedColumns(ingestedColumns.value)
    appStore.setIngestedTableName(ingestedTableName.value)
    appStore.setSchemaFileId(result.file_path || file.name)
    showMessage(`Loaded "${file.name}" → table "${ingestedTableName.value}" (${result.row_count || '?'} rows, ${ingestedColumns.value.length} columns)`, 'success')
  } catch (error) {
    console.error('File upload failed:', error)
    showMessage(`Failed to load file: ${error.message}`, 'error')
  } finally {
    isPickingFile.value = false
  }
}

// Try to prefill the Data Domain Context if a schema already exists for this file
async function tryPrefillContextFromExistingSchema() {
  return
}

// Update check
async function checkForUpdate(silent = false) {
  if (!hasApiKey.value) return
  if (!silent) {
    isCheckingUpdate.value = true
    updateInfo.value = null
    lastUpdateCheck.value = null
  }
  try {
    if (!silent) {
      // Lightweight progress cue while checking
      showProgress('Checking if data re-creation is needed...', 5)
    }
    const resp = await apiService.checkUpdate()
    updateInfo.value = resp
    lastUpdateCheck.value = new Date()
  } catch (e) {
    // Non-blocking: show an inline message but don’t stop user actions
    showMessage('Could not check update status. You can still save settings.', 'error')
  } finally {
    if (!silent) {
      // Do not keep the big progress bar on screen after quick check
      hideProgress()
      isCheckingUpdate.value = false
    }
  }
}

// Event handlers
function handleDataFilePathChange(event) {
  appStore.setDataFilePath(event.target.value)
  clearMessage()
}

function handleSchemaContextChange(event) {
  appStore.setSchemaContext(event.target.value)
  clearMessage()
}

// WebSocket progress handler
function handleProgressUpdate(data) {
  if (data && data.type === 'progress') {
    // Ensure progress UI is visible while backend is reporting work
    if (!isProcessing.value) {
      startTimer()
      isProcessing.value = true
    }

    // Prefer backend message; fallback to stage label
    const msg = data.message || (data.stage ? `Processing: ${data.stage.replace(/_/g, ' ')}` : 'Processing...')

    // Only certain stages provide numeric progress; otherwise keep existing percent
    const stagesWithPercent = new Set(['converting', 'generating_schema'])
    const percent = (data.progress != null && stagesWithPercent.has(data.stage))
      ? data.progress
      : progressPercent.value

    updateProgress(msg, percent)
  }
}

// Schema generation
async function generateAndSaveSchema() {
  try {
    updateProgress('Preparing schema metadata...', 60)
    appStore.setIsSchemaFileUploaded(true)
    appStore.setSchemaFileId(ingestedTableName.value || '')
    updateProgress('Schema metadata ready', 100)
  } catch (error) {
    console.error('❌ Schema generation failed:', error)
    throw error
  }
}

// Main save function — ingestion already done by handleFileSelected.
// This only saves context + generates LLM schema descriptions.
async function saveDataSettings() {
  // Validate API key
  if (!hasApiKey.value) {
    showMessage('Please set your API key in the API tab first.', 'error')
    return
  }

  // Validate that a file has been ingested
  const dataPath = appStore.dataFilePath.trim()
  if (!dataPath) {
    showMessage('Please select a data file first.', 'error')
    return
  }

  if (ingestedColumns.value.length === 0) {
    showMessage('No columns detected. Please re-select the data file.', 'error')
    return
  }

  clearMessage()
  startTimer()
  showProgress('Saving context...', 20)

  try {
    if (ingestedTableName.value) {
      appStore.setSchemaFileId(appStore.dataFilePath)
    }

    await apiService.setContext(appStore.schemaContext.trim())
    await generateAndSaveSchema()

    if (appStore.activeWorkspaceId && ingestedTableName.value) {
      const columnsPayload = ingestedColumns.value.map((col) => ({
        name: col.name,
        dtype: col.type || col.dtype || 'VARCHAR',
        description: col.description || '',
        samples: Array.isArray(col.samples) ? col.samples : []
      }))
      await apiService.v1SyncBrowserDataset(appStore.activeWorkspaceId, {
        table_name: ingestedTableName.value,
        columns: columnsPayload,
        row_count: null
      })
    }

    updateProgress('Data settings saved!', 100)
    showMessage('Data settings saved! Your data is ready for analysis.', 'success')

  } catch (error) {
    console.error('❌ Failed to save data settings:', error)
    showMessage(`Failed to save settings: ${error.message || 'Please try again.'}`, 'error')
  } finally {
    hideProgress()
    updateInfo.value = null
  }
}

// Manual rebuild flow when update is recommended
async function rebuildNow() {
  if (isProcessing.value) return
  // Delegate to the primary save flow to ensure identical behavior
  await saveDataSettings()
}

// Refresh current dataset from source file
async function refreshCurrentDataset() {
  const dataPath = appStore.dataFilePath.trim()
  if (!dataPath || isRefreshing.value) return
  showMessage('Select the file again to refresh browser-loaded data.', 'success')
}

// Cleanup on unmount
onUnmounted(() => {
  stopTimer()
  if (settingsWebSocket) {
    settingsWebSocket.onProgress(null)
  }
  // Remove beforeunload handler
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

// Beforeunload handler to warn user during processing
function handleBeforeUnload(e) {
  if (isProcessing.value) {
    e.preventDefault()
    e.returnValue = 'Data processing is in progress. Leaving may corrupt your data.'
    return e.returnValue
  }
}

// Watch isProcessing to add/remove beforeunload handler
watch(isProcessing, (newVal) => {
  if (newVal) {
    window.addEventListener('beforeunload', handleBeforeUnload)
  } else {
    window.removeEventListener('beforeunload', handleBeforeUnload)
  }
})

// Run update check and auto-detect DuckDB tables when the Data tab mounts
onMounted(async () => {
  checkForUpdate()

  // Pre-populate from existing appStore state
  if (appStore.ingestedTableName) {
    ingestedTableName.value = appStore.ingestedTableName
    ingestedColumns.value = appStore.ingestedColumns || []
  }
})
</script>
