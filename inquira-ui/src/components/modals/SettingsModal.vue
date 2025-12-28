<template>
  <!-- Modal Overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto"
    aria-labelledby="modal-title"
    role="dialog"
    aria-modal="true"
  >
    <!-- Background overlay -->
    <div
      class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
      @click="closeModal"
    ></div>

    <!-- Modal container -->
    <div class="flex min-h-full items-center justify-center p-4">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all mx-auto w-full max-w-4xl max-h-[90vh] flex flex-col"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="bg-white px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900" id="modal-title">
              Application Settings
            </h3>
            <button
              @click="closeModal"
              :disabled="isSavingSettings || isProgressModalVisible"
              class="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XMarkIcon class="h-6 w-6" />
            </button>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="bg-white flex flex-1 overflow-hidden">
          <!-- Sidebar Tabs -->
          <div class="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
            <!-- Tab Navigation -->
            <nav class="flex-1 px-4 py-6 space-y-2">
              <button
                @click="activeTab = 'api'"
                :class="[
                  'w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  activeTab === 'api'
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                ]"
              >
                <KeyIcon class="w-5 h-5 mr-3 flex-shrink-0" />
                <span class="flex-1 text-left">API</span>
                <!-- Warning indicator for missing API key -->
                <ExclamationTriangleIcon
                  v-if="!hasApiKey"
                  class="w-4 h-4 text-yellow-500 flex-shrink-0 ml-2"
                  title="API key is required"
                />
              </button>

              <button
                @click="activeTab = 'data'"
                :class="[
                  'w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  activeTab === 'data'
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                ]"
              >
                <DocumentArrowUpIcon class="w-5 h-5 mr-3 flex-shrink-0" />
                <span class="flex-1 text-left">Data</span>
                <!-- Warning indicator for missing API key -->
                <ExclamationTriangleIcon
                  v-if="!hasApiKey"
                  class="w-4 h-4 text-yellow-500 flex-shrink-0 ml-2"
                  title="API key is required for data configuration"
                />
              </button>

              <button
                @click="activeTab = 'account'"
                :class="[
                  'w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  activeTab === 'account'
                    ? 'bg-purple-100 text-purple-700 border border-purple-200'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                ]"
              >
                <UserIcon class="w-5 h-5 mr-3 flex-shrink-0" />
                <span class="flex-1 text-left">Account</span>
              </button>
            </nav>

            <!-- Sidebar Footer -->
            <div class="px-4 py-4 border-t border-gray-200">
              <div class="text-xs text-gray-500">
                <div class="flex items-center mb-2">
                  <div
                    :class="[
                      'w-2 h-2 rounded-full mr-2',
                      hasApiKey ? 'bg-green-500' : 'bg-yellow-500'
                    ]"
                  ></div>
                  <span>{{ hasApiKey ? 'API Key Set' : 'API Key Missing' }}</span>
                </div>
                <div class="flex items-center">
                  <div
                    :class="[
                      'w-2 h-2 rounded-full mr-2',
                      appStore.canAnalyze ? 'bg-green-500' : 'bg-gray-400'
                    ]"
                  ></div>
                  <span>{{ appStore.canAnalyze ? 'Ready to Analyze' : 'Setup Incomplete' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab Content -->
          <div class="flex-1 overflow-y-auto">
            <!-- Loading State -->
            <div v-if="isLoadingSettings" class="flex items-center justify-center py-12">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span class="ml-3 text-gray-600">Loading settings...</span>
            </div>

            <!-- Tab Content -->
            <div v-else>
              <ApiTab
                v-if="activeTab === 'api'"
                @api-saved="handleApiSaved"
                @api-tested="handleApiTested"
              />
              <DataTab
                v-if="activeTab === 'data'"
                @data-saved="handleDataSaved"
              />
              <AccountTab
                v-if="activeTab === 'account'"
                @password-changed="handlePasswordChanged"
                @account-deleted="handleAccountDeleted"
              />
            </div>
          </div>
        </div>

        <!-- Modal Footer intentionally removed (Close via X in header) -->
      </div>
    </div>
    


    <!-- Settings Progress Modal -->
    <SettingsProgressModal
      :is-visible="isProgressModalVisible"
      :current-message="currentProgressMessage"
      :is-connected="isWebSocketConnected"
      :current-fact="currentFact"
      @cancel="handleProgressCancel"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { apiService } from '../../services/apiService'
import { previewService } from '../../services/previewService'
import { settingsWebSocket } from '../../services/websocketService'
import { factService } from '../../services/factService'
import { toast } from '../../composables/useToast'
import { ref as vueRef } from 'vue'
import SettingsProgressModal from './SettingsProgressModal.vue'
import ApiTab from './ApiTab.vue'
import DataTab from './DataTab.vue'
import AccountTab from './AccountTab.vue'
import {
  XMarkIcon,
  DocumentArrowUpIcon,
  KeyIcon,
  UserIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const appStore = useAppStore()
const isLoadingSettings = ref(false)
const isSavingSettings = ref(false)
const settingsLoaded = ref(false)
const activeTab = ref('api') // 'api' | 'data' | 'account'

// WebSocket and Progress State
const isProgressModalVisible = ref(false)
const currentProgressMessage = ref('Initializing...')
const isWebSocketConnected = ref(false)
const currentFact = ref('')

// Computed properties
const hasApiKey = computed(() => appStore.apiKey.trim() !== '')


function closeModal() {
  // Don't close if currently saving, clearing, or progress modal is visible
  if (isSavingSettings.value || isProgressModalVisible.value) return

  // Stop fact rotation when modal closes
  stopFactRotation()

  emit('close')
}


// Tab event handlers
function handleApiSaved(data) {
  console.log('API settings saved:', data)
  // Could emit an event or update local state if needed
}

function handleApiTested(data) {
  console.log('API key tested:', data)
  // Could emit an event or update local state if needed
}

function handleDataSaved(data) {
  console.log('Data settings saved:', data)
  // Could emit an event or update local state if needed
}

function handlePasswordChanged(data) {
  console.log('Password changed:', data)
  // Could emit an event or update local state if needed
}

function handleAccountDeleted(data) {
  console.log('Account deleted:', data)
  // Could emit an event or update local state if needed
}


// Removed: testFilePath (Test button has been removed)

// Fact rotation functions
async function startFactRotation() {
  try {
    // Load facts if not already loaded
    await factService.loadFacts()

    // Start rotation with callback to update currentFact
    factService.startRotation((newFact) => {
      currentFact.value = newFact
    })

    console.log('🎯 Started fact rotation every 5 seconds for WebSocket connection')
  } catch (error) {
    console.error('❌ Failed to start fact rotation:', error)
  }
}

function stopFactRotation() {
  factService.stopRotation()
  currentFact.value = ''
  console.log('🛑 Stopped fact rotation')
}

// WebSocket event handlers
// Keep reference to unsubscribe function to avoid leaking listeners
const unsubscribeConnection = vueRef(null)

function setupWebSocketHandlers() {
  // Clear previous connection listener if any
  if (typeof unsubscribeConnection.value === 'function') {
    unsubscribeConnection.value()
    unsubscribeConnection.value = null
  }
  settingsWebSocket.onProgress((data) => {
    updateProgressStep(data)
  })

  settingsWebSocket.onComplete((result) => {
    handleSaveComplete(result)
  })

  settingsWebSocket.onError((error) => {
    handleSaveError(error)
  })

  unsubscribeConnection.value = settingsWebSocket.onConnection((connected) => {
    isWebSocketConnected.value = connected
    console.log('WebSocket connection state changed:', connected)

    // Start fact rotation when WebSocket connects
    if (connected) {
      startFactRotation()
    } else {
      stopFactRotation()
    }
  })
}

function updateProgressStep(data) {
  // Handle connection status
  if (data.type === 'connected') {
    isWebSocketConnected.value = true
    return
  }

  // Handle progress updates - display message directly
  if (data.type === 'progress') {
    currentProgressMessage.value = data.message || 'Processing...'

    // Update current fact if provided
    if (data.fact) {
      currentFact.value = data.fact
    }
  }
}

function handleSaveComplete(result) {
  console.log('Settings save completed:', result)

  // Update progress message for completion
  currentProgressMessage.value = 'All settings saved successfully'

  // Start prefetching immediately but keep modal visible to show progress
  setTimeout(async () => {
    try {
      // Generate and save schema
      await generateAndSaveSchema()

      // Clear old preview cache and prefetch new data for faster loading when user opens preview modal
      console.log('🔄 Clearing old cache and prefetching new data preview and schema...')

      // Update progress message for prefetching
      currentProgressMessage.value = 'Preparing data preview for faster loading...'

      // Clear any existing preview cache to ensure fresh data
      previewService.clearPreviewCache()

      // Prefetch data preview
      try {
        await previewService.getDataPreview('random', false) // Use cached version, don't force refresh
        console.log('✅ Data preview prefetched successfully')
      } catch (prefetchError) {
        console.warn('⚠️ Data preview prefetch failed, but settings save was successful:', prefetchError)
        // Don't show error to user - prefetch failure shouldn't affect settings save success
      }

      // Prefetch schema data (only if we have a valid data file path)
      if (appStore.dataFilePath.trim()) {
        try {
          await previewService.loadSchema(appStore.dataFilePath.trim(), false) // Use cached version, don't force refresh
          console.log('✅ Schema data prefetched successfully')
        } catch (schemaPrefetchError) {
          console.warn('⚠️ Schema prefetch failed, but settings save was successful:', schemaPrefetchError)
          // Don't show error to user - prefetch failure shouldn't affect settings save success
        }
      }

      // Update final message
      currentProgressMessage.value = 'Data preview ready for instant loading'

      // Close progress modal after showing completion
      setTimeout(() => {
        isProgressModalVisible.value = false
        isSavingSettings.value = false

        // Remove modal's connection listener
        if (typeof unsubscribeConnection.value === 'function') {
          unsubscribeConnection.value()
          unsubscribeConnection.value = null
        }

        toast.success('Settings Saved', 'Your settings have been saved successfully! Data preview is ready for instant loading.')

        emit('close')
      }, 1500) // Show completion for 1.5 seconds

    } catch (error) {
      console.error('❌ Error during post-save operations:', error)

      // Close progress modal even if post-save operations fail
      setTimeout(() => {
        isProgressModalVisible.value = false
        isSavingSettings.value = false

        // Remove modal's connection listener
        if (typeof unsubscribeConnection.value === 'function') {
          unsubscribeConnection.value()
          unsubscribeConnection.value = null
        }

        emit('close')
      }, 1000)
    }
  }, 500) // Start prefetching after 0.5 seconds to allow other steps to complete
}

function handleSaveError(error) {
  console.error('Settings save error:', error)

  // Update progress message for error
  currentProgressMessage.value = `Error: ${error.message || 'An error occurred while saving settings'}`

  // Close progress modal after showing error
  setTimeout(() => {
    isProgressModalVisible.value = false
    isSavingSettings.value = false

    // Remove modal's connection listener
    if (typeof unsubscribeConnection.value === 'function') {
      unsubscribeConnection.value()
      unsubscribeConnection.value = null
    }

    toast.error('Save Failed', error || 'An error occurred while saving settings')
  }, 3000)
}

function handleProgressCancel() {
  console.log('User cancelled progress')

  // Stop fact rotation
  stopFactRotation()

  // Remove modal's connection listener
  if (typeof unsubscribeConnection.value === 'function') {
    unsubscribeConnection.value()
    unsubscribeConnection.value = null
  }

  // Reset progress state
  isProgressModalVisible.value = false
  isSavingSettings.value = false

  // Reset progress message
  currentProgressMessage.value = 'Initializing...'

  // Connection state will be updated by the onConnection callback
}

// Settings management methods
async function fetchSettings() {
  if (isLoadingSettings.value) return

  isLoadingSettings.value = true
  settingsLoaded.value = false

  try {
    // Fetch main settings
    const settings = await apiService.getSettings()
    console.log('Fetched settings:', settings)

    // Update app store with backend settings
    if (settings.api_key) {
      appStore.setApiKey(settings.api_key)
    }
    if (settings.data_path) {
      appStore.setDataFilePath(settings.data_path)
    }
    if (settings.context) {
      appStore.setSchemaContext(settings.context)
    }


    settingsLoaded.value = true
  } catch (error) {
    console.error('Failed to fetch settings:', error)
    // If settings don't exist yet, that's okay - user can set them
    settingsLoaded.value = true
  } finally {
    isLoadingSettings.value = false
  }
}




// Generate and save schema synchronously (keeps loading state active)
async function generateAndSaveSchema() {
  try {
    // Only attempt schema generation if we have a valid data file path
    if (!appStore.dataFilePath.trim()) {
      console.log('ℹ️ Skipping schema generation - no data file path provided')
      return
    }

    // Verify authentication is still valid before schema generation
    console.log('🔐 Verifying authentication for schema generation...')
    try {
      await apiService.verifyAuth()
      console.log('✅ Authentication verified for schema generation')
    } catch (authError) {
      console.error('❌ Authentication failed for schema generation:', authError)
      toast.warning('Schema Generation Skipped', 'Authentication expired. You can generate schema manually later.')
      return
    }

    // Check if schema already exists to avoid unnecessary regeneration
    try {
      console.log('🔍 Checking if schema already exists...')
      const existingSchema = await apiService.loadSchema(appStore.dataFilePath.trim())

      if (existingSchema && existingSchema.fields && existingSchema.fields.length > 0) {
        console.log('✅ Schema already exists, skipping regeneration')

        // Update store to reflect existing schema
        appStore.setIsSchemaFileUploaded(true)
        appStore.setSchemaFileId(appStore.dataFilePath.trim())

        toast.info('Schema Already Exists', 'Using existing schema for the data file.')
        return
      }
    } catch (error) {
      // Schema doesn't exist, continue with generation
      console.log('ℹ️ Schema does not exist, proceeding with generation')
    }

    console.log('🔄 Generating schema...')

    // Generate schema using the saved data file path and context
    const schemaData = await apiService.generateSchema(
      appStore.dataFilePath.trim(),
      appStore.schemaContext.trim() || null
    )

    console.log('✅ Schema generated successfully:', schemaData)

    // Save the generated schema
    if (schemaData && schemaData.columns) {
      const saveResponse = await apiService.saveSchema(
        appStore.dataFilePath.trim(),
        appStore.schemaContext.trim() || null,
        schemaData.columns
      )

      console.log('💾 Schema saved successfully:', saveResponse)

      // Update the store to reflect that schema is now available
      appStore.setIsSchemaFileUploaded(true)
      appStore.setSchemaFileId(saveResponse.id || appStore.dataFilePath.trim())

      // Show success message for schema generation
      toast.success('Schema Generated', 'Schema has been generated and saved successfully.')
    } else {
      console.warn('⚠️ No schema columns generated, skipping save')
      toast.warning('Schema Generation Incomplete', 'No schema columns were generated.')
    }

  } catch (error) {
    // Show user-friendly error message for schema generation failures
    console.error('❌ Schema generation failed:', error)

    // Log specific error details for debugging
    if (error.response?.status === 401) {
      toast.warning('Schema Generation Failed', 'Authentication expired. Please log in again to generate schema.')
    } else if (error.response?.status === 404) {
      toast.error('File Not Found', 'Data file not found. Please check the file path.')
    } else if (error.response?.status === 400) {
      toast.error('Schema Generation Failed', 'Please check your data file format.')
    } else {
      toast.warning('Schema Generation Failed', 'You can try generating it manually later.')
    }

    // Don't throw error - allow settings save to complete even if schema generation fails
  }
}

// Watch for modal open/close to fetch settings
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    fetchSettings()
  }
})

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && props.isOpen && !isSavingSettings.value && !isProgressModalVisible.value) {
    closeModal()
  }
})
</script>
