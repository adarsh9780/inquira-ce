<template>
  <div class="p-6">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
      <KeyIcon class="w-6 h-6 mr-2 text-green-600" />
      API Configuration
    </h2>

    <!-- Success/Error Messages -->
    <div v-if="message" :class="messageTypeClass" class="mb-4 p-3 rounded-md flex items-center">
      <CheckCircleIcon v-if="messageType === 'success'" class="w-5 h-5 mr-2" />
      <ExclamationTriangleIcon v-else class="w-5 h-5 mr-2" />
      <span class="text-sm">{{ message }}</span>
    </div>

    <div class="space-y-6">
      <!-- Model Selector -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Language Model
        </label>
        <div class="max-w-xs">
          <ModelSelector
            :selected-model="appStore.selectedModel"
            @model-changed="handleModelChange"
          />
        </div>
        <p class="mt-1 text-xs text-gray-500">
          Choose the AI model for data analysis
        </p>
      </div>

      <!-- API Key Input -->
      <div>
        <label for="api-key-input" class="block text-sm font-medium text-gray-700 mb-2">
          Gemini API Key
        </label>
        <div class="relative max-w-md">
          <input
            id="api-key-input"
            :type="showApiKey ? 'text' : 'password'"
            :value="appStore.apiKey"
            @input="handleApiKeyChange"
            placeholder="Enter your Gemini API key"
            class="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            @click="showApiKey = !showApiKey"
            class="absolute inset-y-0 right-0 pr-3 flex items-center"
            type="button"
          >
            <EyeIcon v-if="!showApiKey" class="w-4 h-4 text-gray-400 hover:text-gray-600" />
            <EyeSlashIcon v-else class="w-4 h-4 text-gray-400 hover:text-gray-600" />
          </button>
        </div>
        <div class="mt-2 flex items-center justify-between">
          <p class="text-xs text-gray-500">
            Your API key is stored locally and never shared.
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noopener"
              class="text-blue-600 hover:underline ml-1"
            >
              Get a Gemini API key
            </a>
          </p>
          <button
            @click="testApiKey"
            :disabled="isTestingApiKey || !appStore.apiKey.trim()"
            class="ml-4 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Test your API key with Gemini"
            type="button"
          >
            <span v-if="!isTestingApiKey">Test</span>
            <span v-else class="inline-flex items-center">
              <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-700 mr-2"></div>
              Testing...
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Save Button -->
    <div class="mt-8 pt-4 border-t border-gray-200">
      <button
        @click="saveApiSettings"
        :disabled="isSaving"
        class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <span v-if="isSaving" class="inline-flex items-center">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
          Saving...
        </span>
        <span v-else>Save API Settings</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { apiService } from '../../services/apiService'
import { toast } from '../../composables/useToast'
import ModelSelector from '../ui/ModelSelector.vue'
import {
  KeyIcon,
  EyeIcon,
  EyeSlashIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const showApiKey = ref(false)
const isTestingApiKey = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref('') // 'success' | 'error'

const messageTypeClass = computed(() => {
  return messageType.value === 'success'
    ? 'bg-green-50 border border-green-200 text-green-800'
    : 'bg-red-50 border border-red-200 text-red-800'
})

function handleModelChange(model) {
  appStore.setSelectedModel(model)
  clearMessage()
}

function handleApiKeyChange(event) {
  appStore.setApiKey(event.target.value)
  clearMessage()
}

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

async function testApiKey() {
  const key = appStore.apiKey.trim()
  if (!key) {
    message.value = 'Please enter your Gemini API key first.'
    messageType.value = 'error'
    return
  }

  isTestingApiKey.value = true
  clearMessage()

  try {
    const res = await apiService.testGeminiApi(key)
    message.value = res?.detail || 'Successfully connected to Gemini API.'
    messageType.value = 'success'
  } catch (error) {
    console.error('❌ Gemini API test failed:', error)
    const errorMessage = error.response?.data?.detail || error.data?.detail || error.message || 'Failed to validate API key.'
    message.value = errorMessage
    messageType.value = 'error'
  } finally {
    isTestingApiKey.value = false
  }
}

async function saveApiSettings() {
  const apiKey = appStore.apiKey.trim()
  const selectedModel = appStore.selectedModel

  // Validate API key
  if (!apiKey) {
    message.value = 'API key is required.'
    messageType.value = 'error'
    return
  }

  isSaving.value = true
  clearMessage()

  try {
    // Test API key first
    await testApiKey()

    // If test was successful, save settings
    if (messageType.value === 'success') {
      await apiService.setApiKeySettings(apiKey)
      // Note: Model settings might need a separate endpoint
      // await apiService.setModelSettings(selectedModel)

      message.value = 'API settings saved successfully.'
      messageType.value = 'success'
    }
  } catch (error) {
    console.error('❌ Failed to save API settings:', error)
    message.value = 'Failed to save API settings. Please try again.'
    messageType.value = 'error'
  } finally {
    isSaving.value = false
  }
}
</script>