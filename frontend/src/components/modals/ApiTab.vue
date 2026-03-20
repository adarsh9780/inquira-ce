<template>
  <div class="p-6">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
      <KeyIcon class="w-6 h-6 mr-2 text-green-600" />
      Models Configuration
    </h2>

    <!-- Success/Error Messages -->
    <div v-if="message" :class="messageTypeClass" class="mb-4 p-3 rounded-md flex items-center">
      <CheckCircleIcon v-if="messageType === 'success'" class="w-5 h-5 mr-2" />
      <ExclamationTriangleIcon v-else class="w-5 h-5 mr-2" />
      <span class="text-sm">{{ message }}</span>
    </div>

    <div class="space-y-6">
      <div>
        <div class="max-w-md mb-2 flex items-center justify-between gap-2">
          <label class="block text-sm font-medium" style="color: var(--color-text-main);">
            Provider
          </label>
          <button
            @click="refreshProviderModels"
            :disabled="isRefreshingModels || isSaving"
            class="px-2.5 py-1 text-xs rounded-md border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style="border-color: var(--color-border); color: var(--color-text-main); background-color: var(--color-surface);"
            type="button"
          >
            <span v-if="!isRefreshingModels">Refresh Models</span>
            <span v-else class="inline-flex items-center">
              <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-700 mr-2"></div>
              Refreshing...
            </span>
          </button>
        </div>
        <HeaderDropdown
          :model-value="appStore.llmProvider"
          @update:model-value="handleProviderChange"
          :options="providerOptions"
          placeholder="Select provider"
          max-width-class="max-w-md w-full"
        />
      </div>

      <div
        v-if="openrouterNeedsAccountModels"
        class="max-w-md rounded-md border p-3 text-xs"
        style="border-color: #f5c26b; background-color: #fff8e8; color: #8a5a00;"
      >
        OpenRouter account-level models are not configured yet. Configure account models first, then refresh this list.
        Until then, the default model is openrouter/free.
        <a
          :href="openrouterAccountModelsUrl"
          @click.prevent="openLink(openrouterAccountModelsUrl)"
          target="_blank"
          rel="noopener"
          class="ml-1 underline"
          style="color: #8a5a00;"
        >
          Open account model settings
        </a>
        .
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
          :searchable="true"
          :group-by-provider="true"
          search-placeholder="Search models"
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
          :searchable="true"
          :group-by-provider="true"
          search-placeholder="Search models"
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
          :searchable="true"
          :group-by-provider="true"
          search-placeholder="Search models"
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
              @click.prevent="openLink(providerKeyUrl)"
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
        <span v-else>Save Model Settings</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { apiService } from '../../services/apiService'
import { openExternalUrl } from '../../services/externalLinkService'
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
const isRefreshingModels = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref('') // 'success' | 'error'

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
const providerCatalog = computed(() => appStore.providerModelCatalogs?.[appStore.llmProvider] || {})
const openrouterNeedsAccountModels = computed(() => (
  appStore.llmProvider === 'openrouter' && providerCatalog.value?.account_models_configured === false
))
const openrouterAccountModelsUrl = computed(() => (
  String(providerCatalog.value?.account_models_url || 'https://openrouter.ai/settings').trim()
))
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

function clearMessage() {
  message.value = ''
  messageType.value = ''
}

function openLink(url) {
  void openExternalUrl(url)
}

function extractErrorMessage(error, fallback = 'Request failed. Please try again.') {
  return error?.response?.data?.detail || error?.data?.detail || error?.message || fallback
}

async function refreshProviderModels() {
  isRefreshingModels.value = true
  clearMessage()

  try {
    const payload = { provider: appStore.llmProvider }
    const key = appStore.apiKey.trim()
    if (key) payload.api_key = key
    const response = await apiService.v1RefreshProviderModels(payload)
    if (typeof appStore.applyPreferencesResponse === 'function') {
      appStore.applyPreferencesResponse(response)
    }
    syncProviderCatalog(appStore.llmProvider)
    message.value = response?.detail || `Refreshed models for provider '${appStore.llmProvider}'.`
    messageType.value = 'success'
  } catch (error) {
    console.error('❌ Failed to refresh provider models:', error)
    message.value = extractErrorMessage(error, 'Failed to refresh provider models.')
    messageType.value = 'error'
  } finally {
    isRefreshingModels.value = false
  }
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
    message.value = extractErrorMessage(error, 'Failed to validate API key.')
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
    message.value = extractErrorMessage(error, 'Failed to save model settings. Please try again.')
    messageType.value = 'error'
  } finally {
    isSaving.value = false
  }
}

</script>
