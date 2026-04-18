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
            API Provider
          </label>
          <div :title="refreshModelsTooltip">
            <button
              @click="refreshProviderModels"
              :disabled="isRefreshModelsDisabled"
              class="px-2.5 py-1 text-xs rounded-md border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style="border-color: var(--color-border); color: var(--color-text-main); background-color: var(--color-surface);"
              type="button"
            >
              <span v-if="!isRefreshingModels">Refresh Models</span>
              <span v-else class="inline-flex items-center">
                <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-[var(--color-accent)] mr-2"></div>
                Refreshing...
              </span>
            </button>
          </div>
        </div>
        <HeaderDropdown
          :model-value="appStore.llmProvider"
          @update:model-value="handleProviderChange"
          :options="providerOptions"
          placeholder="Select provider"
          max-width-class="max-w-md w-full"
        />
      </div>

      <div v-if="requiresApiKey">
        <label for="api-key-input" class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          API Key ({{ appStore.llmProvider }})
        </label>
        <div class="max-w-md">
          <div class="flex items-center gap-2">
            <div class="relative flex-1">
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
            <div class="flex items-center gap-2">
              <button
                @click="verifyAndSaveProviderConfig"
                :disabled="isSavingApiKey || !appStore.apiKey.trim()"
                class="inline-flex h-9 min-w-[7rem] items-center justify-center px-3 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed btn-primary"
                title="Verify key, save provider config, and refresh model catalog"
                type="button"
              >
                <span v-if="!isSavingApiKey">Verify &amp; Save</span>
                <span v-else class="inline-flex items-center">
                  <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-[var(--color-accent)] mr-2"></div>
                  Verifying...
                </span>
              </button>
            </div>
          </div>
          <p class="mt-2 text-xs" style="color: var(--color-text-muted);">
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
        </div>
      </div>

      <div v-else class="space-y-3 max-w-md">
        <p class="text-xs text-green-700">
          Ollama does not require an API key.
        </p>
        <div>
          <label for="ollama-base-url" class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
            Ollama Base URL
          </label>
          <input
            id="ollama-base-url"
            type="text"
            v-model="ollamaBaseUrl"
            placeholder="http://localhost:11434"
            class="input-base"
          />
        </div>
        <button
          @click="verifyAndSaveProviderConfig"
          :disabled="isSavingApiKey"
          class="inline-flex h-9 min-w-[8rem] items-center justify-center px-3 text-xs font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed btn-primary"
          type="button"
        >
          <span v-if="!isSavingApiKey">Verify &amp; Save</span>
          <span v-else class="inline-flex items-center">
            <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-[var(--color-accent)] mr-2"></div>
            Verifying...
          </span>
        </button>
      </div>

      <p v-if="requiresApiKey && appStore.selectedProviderApiKeyPresent" class="text-xs text-green-700">
        A key for {{ appStore.llmProvider }} is already configured in secure storage.
      </p>

      <div
        v-if="requiresApiKey && !hasSavedProviderApiKey"
        class="max-w-md rounded-md border p-3 text-xs"
        style="border-color: var(--color-border); background-color: var(--color-surface-subtle); color: var(--color-text-muted);"
      >
        The models shown below are built-in defaults. Save your API key first, then refresh to load models for this provider.
      </div>

      <div
        v-if="openrouterNeedsAccountModels"
        class="max-w-md rounded-md border p-3 text-xs"
        style="border-color: var(--color-warning); background-color: var(--color-warning-bg); color: var(--color-warning-text);"
      >
        OpenRouter account-level models are not configured yet. Configure account models first, then refresh this list.
        Until then, the default model is openrouter/free.
        <a
          :href="openrouterAccountModelsUrl"
          @click.prevent="openLink(openrouterAccountModelsUrl)"
          target="_blank"
          rel="noopener"
          class="ml-1 underline"
          style="color: var(--color-warning-text);"
        >
          Open account model settings
        </a>
        .
      </div>

      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--color-text-main);">
          Main Model (shown in Chat selector)
        </label>
        <div class="max-w-md">
          <ModelSelector
            :selected-model="appStore.selectedModel"
            :provider="appStore.llmProvider"
            :model-options="appStore.providerMainModels"
            :backend-search="searchProviderModels"
            :search-loading="appStore.providerModelSearchLoading"
            :search-debounce-ms="250"
            :max-options-without-search="10"
            @model-changed="handleMainModelChange"
          />
        </div>
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

    </div>

    <!-- Save Button -->
    <div class="mt-8 pt-4 border-t" style="border-color: var(--color-border);">
      <button
        @click="saveApiSettings"
        :disabled="isSavingSettings || isSavingApiKey"
        class="w-full px-4 py-2 btn-primary"
      >
        <span v-if="isSavingSettings" class="inline-flex items-center">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
          Saving...
        </span>
        <span v-else>Save Model Settings</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { apiService } from '../../services/apiService'
import { openExternalUrl } from '../../services/externalLinkService'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
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
const isRefreshingModels = ref(false)
const isSavingApiKey = ref(false)
const isSavingSettings = ref(false)
const ollamaBaseUrl = ref('http://localhost:11434')
const message = ref('')
const messageType = ref('') // 'success' | 'error' | 'warning'

const providerOptions = computed(() => appStore.availableProviders.map(p => ({ label: p, value: p })))
const liteModelOptions = computed(() => appStore.providerLiteModels.map(m => ({ label: m, value: m })))

const messageTypeClass = computed(() => {
  if (messageType.value === 'success') {
    return 'bg-green-50 border border-green-200 text-green-800'
  }
  if (messageType.value === 'warning') {
    return 'bg-yellow-50 border border-yellow-200 text-yellow-800'
  }
  return 'bg-red-50 border border-red-200 text-red-800'
})
const requiresApiKey = computed(() => !!appStore.providerRequiresApiKey)
const hasSavedProviderApiKey = computed(() => !requiresApiKey.value || !!appStore.selectedProviderApiKeyPresent)
const providerCatalog = computed(() => appStore.providerModelCatalogs?.[appStore.llmProvider] || {})
const openrouterNeedsAccountModels = computed(() => (
  appStore.llmProvider === 'openrouter' && providerCatalog.value?.account_models_configured === false
))
const isRefreshModelsDisabled = computed(() => (
  isRefreshingModels.value || isSavingApiKey.value || isSavingSettings.value || !hasSavedProviderApiKey.value
))
const refreshModelsTooltip = computed(() => {
  if (isRefreshModelsDisabled.value && requiresApiKey.value && !hasSavedProviderApiKey.value) {
    return `Save your ${appStore.llmProvider} API key first to refresh models.`
  }
  return 'Refresh models from the configured provider'
})
const openrouterAccountModelsUrl = computed(() => (
  String(providerCatalog.value?.account_models_url || 'https://openrouter.ai/settings').trim()
))
const providerKeyUrl = computed(() => {
  if (appStore.llmProvider === 'openai') return 'https://platform.openai.com/api-keys'
  if (appStore.llmProvider === 'anthropic') return 'https://console.anthropic.com/settings/keys'
  return 'https://openrouter.ai/keys'
})

function syncOllamaBaseUrl() {
  const catalogBaseUrl = String(appStore.providerModelCatalogs?.ollama?.base_url || '').trim()
  ollamaBaseUrl.value = catalogBaseUrl || 'http://localhost:11434'
}

watch(
  () => appStore.llmProvider,
  (provider) => {
    if (provider === 'ollama') {
      syncOllamaBaseUrl()
    }
  },
  { immediate: true }
)

function handleApiKeyChange(event) {
  appStore.setApiKey(event.target.value)
  clearMessage()
}

function handleProviderChange(event) {
  const provider = String(event?.target?.value ?? event ?? '').trim().toLowerCase()
  appStore.setLlmProvider(provider)
  appStore.setApiKey('')
  if (provider === 'ollama') {
    syncOllamaBaseUrl()
  }
  clearMessage()
}

function handleLiteModelChange(event) {
  appStore.setSelectedLiteModel(event?.target?.value ?? event)
  clearMessage()
}

function handleMainModelChange(event) {
  appStore.setSelectedModel(event?.target?.value ?? event)
  clearMessage()
}

async function searchProviderModels(query, limit = 25) {
  const models = await appStore.searchProviderModels(query, limit)
  return Array.isArray(models) ? models : []
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
  if (isRefreshModelsDisabled.value) return
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
    if (appStore.llmProvider === 'ollama') {
      syncOllamaBaseUrl()
    }
    message.value = response?.detail || `Refreshed models for provider '${appStore.llmProvider}'.`
    messageType.value = response?.error ? 'warning' : 'success'
  } catch (error) {
    console.error('❌ Failed to refresh provider models:', error)
    message.value = extractErrorMessage(error, 'Failed to refresh provider models.')
    messageType.value = 'error'
  } finally {
    isRefreshingModels.value = false
  }
}

async function verifyAndSaveProviderConfig() {
  const key = appStore.apiKey.trim()
  if (requiresApiKey.value && !key) {
    message.value = 'Please enter your API key first.'
    messageType.value = 'error'
    return
  }

  isSavingApiKey.value = true
  clearMessage()

  try {
    const payload = {
      provider: appStore.llmProvider,
      selected_model: appStore.selectedModel,
      selected_lite_model: appStore.selectedLiteModel,
      selected_coding_model: appStore.selectedModel,
    }
    if (requiresApiKey.value) {
      payload.api_key = key
    } else {
      payload.base_url = String(ollamaBaseUrl.value || '').trim() || 'http://localhost:11434'
    }

    const response = await apiService.setApiKeySettings(payload, appStore.llmProvider)
    if (response && typeof appStore.applyPreferencesResponse === 'function') {
      appStore.applyPreferencesResponse(response)
    }
    if (appStore.llmProvider === 'ollama') {
      syncOllamaBaseUrl()
    }

    const refreshedCount = Array.isArray(response?.provider_available_main_models)
      ? response.provider_available_main_models.length
      : 0
    if (response?.warning) {
      message.value = 'Key saved. Model refresh failed. Use Refresh Models to retry.'
      messageType.value = 'warning'
    } else {
      message.value = `Provider saved. Refreshed ${refreshedCount} models.`
      messageType.value = 'success'
    }
  } catch (error) {
    console.error('❌ Failed to verify and save provider config:', error)
    message.value = extractErrorMessage(error, 'Failed to verify and save provider configuration.')
    messageType.value = 'error'
  } finally {
    isSavingApiKey.value = false
  }
}

async function saveApiSettings() {
  if (!appStore.availableModels.length) {
    message.value = 'No main models available for provider.'
    messageType.value = 'error'
    return
  }

  isSavingSettings.value = true
  clearMessage()

  try {
    const response = await apiService.v1UpdatePreferences({
      llm_provider: appStore.llmProvider,
      selected_model: appStore.selectedModel,
      selected_lite_model: appStore.selectedLiteModel,
      selected_coding_model: appStore.selectedModel,
    })
    
    // Sync store state with backend response (especially providerRequiresApiKey)
    if (typeof appStore.applyPreferencesResponse === 'function') {
      appStore.applyPreferencesResponse(response)
    }
    message.value = 'Provider and model settings saved.'
    messageType.value = 'success'
  } catch (error) {
    console.error('❌ Failed to save API settings:', error)
    message.value = extractErrorMessage(error, 'Failed to save model settings. Please try again.')
    messageType.value = 'error'
  } finally {
    isSavingSettings.value = false
  }
}

</script>
