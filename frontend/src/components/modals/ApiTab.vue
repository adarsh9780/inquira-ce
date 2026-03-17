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
      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          Provider
        </label>
        <HeaderDropdown
          :model-value="appStore.llmProvider"
          @update:model-value="handleProviderChange"
          :options="providerOptions"
          placeholder="Select provider"
          max-width-class="max-w-md w-full"
        />
      </div>

      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          Main Models (shown in Chat selector)
        </label>
        <MultiSelectDropdown
          :model-value="appStore.availableModels"
          @update:model-value="handleMainModelsChange"
          :options="mainModelOptions"
          placeholder="Select main models"
          max-width-class="max-w-md w-full"
        />
      </div>

      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          Lite Model
        </label>
        <HeaderDropdown
          :model-value="appStore.selectedLiteModel"
          @update:model-value="handleLiteModelChange"
          :options="liteModelOptions"
          placeholder="Select lite model"
          max-width-class="max-w-md w-full"
        />
      </div>

      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          Coding Model (subagent)
        </label>
        <HeaderDropdown
          :model-value="appStore.selectedCodingModel"
          @update:model-value="handleCodingModelChange"
          :options="codingModelOptions"
          placeholder="Select coding model"
          max-width-class="max-w-md w-full"
        />
      </div>

      <!-- API Key Input -->
      <div v-if="requiresApiKey">
        <label for="api-key-input" class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          API Key ({{ appStore.llmProvider }})
        </label>
        <div class="relative max-w-md">
          <input
            id="api-key-input"
            :type="showApiKey ? 'text' : 'password'"
            :value="appStore.apiKey"
            @input="handleApiKeyChange"
            :placeholder="`Enter your ${appStore.llmProvider} API key`"
            class="input-base pr-10"
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
          <p class="text-xs" style="color: var(--color-text-muted);">
            Your API key is stored in your OS keychain.
            <a
              :href="providerKeyUrl"
              target="_blank"
              rel="noopener"
              class="hover:underline ml-1"
              style="color: var(--color-accent);"
            >
              Get a {{ appStore.llmProvider }} API key
            </a>
          </p>
          <button
            @click="testApiKey"
            :disabled="isTestingApiKey || !appStore.apiKey.trim() || !appStore.selectedModel"
            class="ml-4 px-3 py-1.5 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed btn-secondary"
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

      <p v-else class="text-xs text-green-700">
        Ollama does not require an API key.
      </p>

      <p v-if="requiresApiKey && appStore.selectedProviderApiKeyPresent" class="text-xs text-green-700">
        A key for {{ appStore.llmProvider }} is already configured in secure storage.
      </p>

      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
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
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          Runner Packages
        </label>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl">
          <input
            v-model="runnerPackageName"
            type="text"
            placeholder="Package name (e.g. scikit-learn)"
            class="input-base"
          />
          <input
            v-model="runnerPackageVersion"
            type="text"
            placeholder="Exact version (e.g. 1.5.2)"
            class="input-base"
          />
          <input
            v-model="runnerIndexUrl"
            type="text"
            placeholder="Index URL (optional)"
            class="sm:col-span-2 input-base"
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
            class="px-3 py-2 text-sm font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed btn-secondary"
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
    <div class="mt-8 pt-4 border-t" style="border-color: var(--color-border);">
      <button
        @click="saveApiSettings"
        :disabled="isSaving"
        class="w-full px-4 py-2 btn-primary"
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
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import MultiSelectDropdown from '../ui/MultiSelectDropdown.vue'
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

const providerOptions = computed(() => appStore.availableProviders.map(p => ({ label: p, value: p })))
const mainModelOptions = computed(() => appStore.providerMainModels.map(m => ({ label: m, value: m })))
const liteModelOptions = computed(() => appStore.providerLiteModels.map(m => ({ label: m, value: m })))
const codingModelOptions = computed(() => appStore.availableModels.map(m => ({ label: m, value: m })))

const messageTypeClass = computed(() => {
  return messageType.value === 'success'
    ? 'bg-green-50 border border-green-200 text-green-800'
    : 'bg-red-50 border border-red-200 text-red-800'
})
const requiresApiKey = computed(() => !!appStore.providerRequiresApiKey)
const providerKeyUrl = computed(() => {
  if (appStore.llmProvider === 'openai') return 'https://platform.openai.com/api-keys'
  if (appStore.llmProvider === 'anthropic') return 'https://console.anthropic.com/settings/keys'
  return 'https://openrouter.ai/keys'
})

function syncProviderCatalog(provider) {
  const catalog = appStore.providerModelCatalogs?.[provider] || {}
  const mainModels = Array.isArray(catalog.main_models) ? catalog.main_models : []
  const liteModels = Array.isArray(catalog.lite_models) ? catalog.lite_models : []
  if (mainModels.length) {
    appStore.providerMainModels = [...mainModels]
    const enabled = appStore.availableModels.filter((item) => mainModels.includes(item))
    appStore.setEnabledModels(enabled.length ? enabled : [...mainModels])
  }
  if (!appStore.availableModels.includes(appStore.selectedModel)) {
    appStore.setSelectedModel(appStore.availableModels[0] || '')
  }
  if (!appStore.availableModels.includes(appStore.selectedCodingModel)) {
    appStore.setSelectedCodingModel(appStore.selectedModel || appStore.availableModels[0] || '')
  }
  if (liteModels.length) {
    appStore.providerLiteModels = [...liteModels]
    const fallbackLite = catalog.default_lite_model || liteModels[0] || ''
    appStore.setSelectedLiteModel(
      liteModels.includes(appStore.selectedLiteModel) ? appStore.selectedLiteModel : fallbackLite
    )
  }
}

function handleApiKeyChange(event) {
  appStore.setApiKey(event.target.value)
  clearMessage()
}

function handleProviderChange(event) {
  const provider = String(event?.target?.value ?? event ?? '').trim().toLowerCase()
  appStore.setLlmProvider(provider)
  appStore.setApiKey('')
  syncProviderCatalog(provider)
  clearMessage()
}

function handleLiteModelChange(event) {
  appStore.setSelectedLiteModel(event?.target?.value ?? event)
  clearMessage()
}

function handleCodingModelChange(event) {
  appStore.setSelectedCodingModel(event?.target?.value ?? event)
  clearMessage()
}

function toggleEnabledModel(model, event) {
  const checked = !!event?.target?.checked
  const current = [...appStore.availableModels]
  const next = checked ? Array.from(new Set([...current, model])) : current.filter((item) => item !== model)
  if (!next.length) {
    message.value = 'Please keep at least one main model enabled.'
    messageType.value = 'error'
    return
  }
  appStore.setEnabledModels(next)
  if (!next.includes(appStore.selectedModel)) {
    appStore.setSelectedModel(next[0])
  }
  if (!next.includes(appStore.selectedCodingModel)) {
    appStore.setSelectedCodingModel(next[0])
  }
  clearMessage()
}

function handleMainModelsChange(next) {
  if (!next || !next.length) {
    message.value = 'Please keep at least one main model enabled.'
    messageType.value = 'error'
    return
  }
  appStore.setEnabledModels(next)
  if (!next.includes(appStore.selectedModel)) {
    appStore.setSelectedModel(next[0])
  }
  if (!next.includes(appStore.selectedCodingModel)) {
    appStore.setSelectedCodingModel(next[0])
  }
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
    const res = await apiService.testGeminiApi(key, appStore.selectedModel, appStore.llmProvider)
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

  if (!appStore.availableModels.length) {
    message.value = 'Select at least one main model.'
    messageType.value = 'error'
    return
  }

  isSaving.value = true
  clearMessage()

  try {
    const response = await apiService.v1UpdatePreferences({
      llm_provider: appStore.llmProvider,
      selected_model: appStore.selectedModel,
      selected_lite_model: appStore.selectedLiteModel,
      selected_coding_model: appStore.selectedCodingModel,
      enabled_models: appStore.availableModels,
      allow_schema_sample_values: appStore.allowSchemaSampleValues,
    })
    
    // Sync store state with backend response (especially providerRequiresApiKey)
    if (typeof appStore.applyPreferencesResponse === 'function') {
      appStore.applyPreferencesResponse(response)
    }

    if (requiresApiKey.value) {
      if (!apiKey) {
        message.value = `API key is required for ${appStore.llmProvider}.`
        messageType.value = 'error'
        return
      }
      await testApiKey()
      if (messageType.value !== 'success') return
      await apiService.setApiKeySettings(apiKey, appStore.llmProvider)
      appStore.setApiKeyConfigured(true)
    }
    await appStore.loadUserPreferences()
    message.value = 'Provider and model settings saved.'
    messageType.value = 'success'
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
