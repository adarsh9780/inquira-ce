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
            :model-options="appStore.availableModels"
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
          API Key (OpenRouter)
        </label>
        <div class="relative max-w-md">
          <input
            id="api-key-input"
            :type="showApiKey ? 'text' : 'password'"
            :value="appStore.apiKey"
            @input="handleApiKeyChange"
            placeholder="Enter your OpenRouter API key"
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
            Your API key is stored in your OS keychain.
            <a
              href="https://openrouter.ai/keys"
              target="_blank"
              rel="noopener"
              class="text-blue-600 hover:underline ml-1"
            >
              Get an OpenRouter API key
            </a>
          </p>
          <button
            @click="testApiKey"
            :disabled="isTestingApiKey || !appStore.apiKey.trim()"
            class="ml-4 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Test your API key with the configured provider"
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

      <p v-if="appStore.apiKeyConfigured" class="text-xs text-green-700">
        A key is already configured in secure storage.
      </p>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Schema Privacy
        </label>
        <label class="inline-flex items-start gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            class="mt-0.5"
            :checked="appStore.allowSchemaSampleValues"
            @change="handleSampleSharingChange"
          />
          <span>Allow sample values in schema generation prompts</span>
        </label>
        <p class="mt-1 text-xs text-gray-500">
          Off by default. When disabled, sample cell values are stripped before schema metadata is saved.
        </p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Runner Packages
        </label>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl">
          <input
            v-model="runnerPackageName"
            type="text"
            placeholder="Package name (e.g. scikit-learn)"
            class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <input
            v-model="runnerPackageVersion"
            type="text"
            placeholder="Exact version (e.g. 1.5.2)"
            class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <input
            v-model="runnerIndexUrl"
            type="text"
            placeholder="Index URL (optional)"
            class="sm:col-span-2 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <label class="mt-2 inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            v-model="saveRunnerDefaults"
            type="checkbox"
            class="mt-0.5"
          />
          <span>Save as default in <code>inquira.toml</code></span>
        </label>
        <div class="mt-3 max-w-2xl">
          <button
            @click="installRunnerPackage"
            :disabled="isInstallingRunnerPackage || !runnerPackageName.trim() || !runnerPackageVersion.trim() || !appStore.activeWorkspaceId"
            type="button"
            class="px-3 py-2 text-sm font-medium text-indigo-700 bg-indigo-100 hover:bg-indigo-200 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="!isInstallingRunnerPackage">Install Runner Package</span>
            <span v-else class="inline-flex items-center">
              <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-indigo-700 mr-2"></div>
              Installing...
            </span>
          </button>
        </div>
        <p class="mt-1 text-xs text-gray-500">
          Installs are restricted to pinned versions (<code>name==version</code>) and run outside analysis execution.
        </p>
        <div v-if="runnerInstallDetails" class="mt-3 max-w-2xl p-3 rounded-md border border-gray-200 bg-gray-50">
          <p class="text-xs font-medium text-gray-700 mb-1">Last install details</p>
          <pre class="text-xs text-gray-700 whitespace-pre-wrap break-words">{{ runnerInstallDetails }}</pre>
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
const isInstallingRunnerPackage = ref(false)
const message = ref('')
const messageType = ref('') // 'success' | 'error'
const runnerPackageName = ref('')
const runnerPackageVersion = ref('')
const runnerIndexUrl = ref('')
const saveRunnerDefaults = ref(false)
const runnerInstallDetails = ref('')

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

function handleSampleSharingChange(event) {
  appStore.setAllowSchemaSampleValues(event.target.checked)
  clearMessage()
}

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

async function testApiKey() {
  const key = appStore.apiKey.trim()
  if (!key) {
    message.value = 'Please enter your API key first.'
    messageType.value = 'error'
    return
  }

  isTestingApiKey.value = true
  clearMessage()

  try {
    const res = await apiService.testGeminiApi(key, appStore.selectedModel)
    message.value = res?.detail || 'Successfully connected to model provider.'
    messageType.value = 'success'
  } catch (error) {
    console.error('❌ Provider API test failed:', error)
    const errorMessage = error.response?.data?.detail || error.data?.detail || error.message || 'Failed to validate API key.'
    message.value = errorMessage
    messageType.value = 'error'
  } finally {
    isTestingApiKey.value = false
  }
}

async function saveApiSettings() {
  const apiKey = appStore.apiKey.trim()

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

    // If test was successful, persist securely for v1 runtime.
    if (messageType.value === 'success') {
      await apiService.setApiKeySettings(apiKey)
      appStore.setApiKeyConfigured(true)
      message.value = 'API key saved securely in OS keychain.'
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

async function installRunnerPackage() {
  const packageName = runnerPackageName.value.trim()
  const version = runnerPackageVersion.value.trim()
  const indexUrl = runnerIndexUrl.value.trim()

  if (!appStore.activeWorkspaceId) {
    message.value = 'Create/select a workspace before installing runner packages.'
    messageType.value = 'error'
    return
  }
  if (!packageName || !version) {
    message.value = 'Package name and exact version are required.'
    messageType.value = 'error'
    return
  }

  isInstallingRunnerPackage.value = true
  clearMessage()
  runnerInstallDetails.value = ''
  try {
    const response = await apiService.v1InstallRunnerPackage({
      workspace_id: appStore.activeWorkspaceId,
      package: packageName,
      version,
      index_url: indexUrl || null,
      save_as_default: saveRunnerDefaults.value
    })
    const installText = response?.package_spec || `${packageName}==${version}`
    const commandText = Array.isArray(response?.command) ? response.command.join(' ') : ''
    const stdoutText = String(response?.stdout || '').trim()
    const stderrText = String(response?.stderr || '').trim()
    runnerInstallDetails.value = [
      commandText ? `Command: ${commandText}` : '',
      stdoutText ? `stdout:\n${stdoutText}` : '',
      stderrText ? `stderr:\n${stderrText}` : '',
    ].filter(Boolean).join('\n\n')
    message.value = `Installed ${installText} using ${response?.installer || 'uv'}. Workspace kernel reset: ${response?.workspace_kernel_reset ? 'yes' : 'no'}.`
    messageType.value = 'success'
    toast.success('Runner Package Installed', message.value)
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to install runner package.'
    const data = error.response?.data || {}
    const command = Array.isArray(data?.command) ? data.command.join(' ') : ''
    const stdoutText = String(data?.stdout || '').trim()
    const stderrText = String(data?.stderr || '').trim()
    runnerInstallDetails.value = [
      command ? `Command: ${command}` : '',
      stdoutText ? `stdout:\n${stdoutText}` : '',
      stderrText ? `stderr:\n${stderrText}` : '',
    ].filter(Boolean).join('\n\n')
    message.value = errorMessage
    messageType.value = 'error'
    toast.error('Install Failed', errorMessage)
  } finally {
    isInstallingRunnerPackage.value = false
  }
}
</script>
